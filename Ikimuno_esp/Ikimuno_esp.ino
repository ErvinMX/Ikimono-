#include <WiFi.h> 
#include <WiFiUdp.h> 
#include <PubSubClient.h> 
#include <Wire.h> 
#include "MAX30105.h" 
#include "heartRate.h" 
#include <driver/i2s.h> 
#include <Adafruit_GC9A01A.h> 
#include <SPI.h> 

// ==================== NETWORK SETTINGS ====================
const char* ssid = ""; //add this
const char* password = ""; //fill in password
const char* target_ip = "172.20.10.4"; // Update IP
const int mqtt_port = 1883; 
const int udp_port = 5005; 

WiFiClient espClient; 
PubSubClient client(espClient); 
WiFiUDP udp; 

// ==================== PIN SETUP ====================
#define SDA_PIN 38 
#define SCL_PIN 39 
#define IMU_ADDR  0x6B 
#define CTRL1_XL  0x10 
#define CTRL2_G   0x11 
#define OUTX_L_G  0x22 

#define I2S_WS    17 
#define I2S_SCK   15 
#define I2S_SD    16 
#define I2S_PORT  I2S_NUM_0 

#define TFT_SCLK  46 
#define TFT_MOSI  9 
#define TFT_CS    12 
#define TFT_DC    11 
#define TFT_RST   10 
#define TFT_BL    13 

// ==================== OBJECTS & GLOBALS ====================
MAX30105 particleSensor; 
Adafruit_GC9A01A tft(TFT_CS, TFT_DC, TFT_RST); 

int16_t gx = 0, gy = 0, gz = 0, ax = 0, ay = 0, az = 0; 
float bpm = 0.0, avgBpm = 0.0; 
bool fingerPresent = false; 
const byte RATE_SIZE = 8; 
byte rates[RATE_SIZE] = {0}; 
byte rateSpot = 0; 
long lastBeat = 0; 

unsigned long lastDisplayUpdate = 0; 
unsigned long lastDataSend = 0; 
float smoothMic = 0.0f; 

String remoteState = "CALM"; 
String lastRemoteState = ""; 
float lastDrawnBpm = -1; 
bool isMicActive = false; 

// ==================== MQTT CALLBACK ====================
void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) message += (char)payload[i]; 
  
  String topicStr = String(topic); 
  if (topicStr == "ikimono/screen/alert") {
    remoteState = message; 
  } else if (topicStr == "ikimono/command/mic") {
    if (message == "ON") {
      isMicActive = true;
      Serial.println("🎤 Mic Activated via MQTT"); 
    } else if (message == "OFF") {
      isMicActive = false;
      Serial.println("🔇 Mic Deactivated via MQTT"); 
    }
  }
}

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200); 
  delay(3000); 
  Serial.println("\n\n--- IKIMUNO SYSTEM BOOTING ---"); 

  // WiFi Connection
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password); 
  while (WiFi.status() != WL_CONNECTED) { 
    delay(500); 
    Serial.print("."); 
  }
  Serial.println("\n✅ WiFi Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  client.setServer(target_ip, mqtt_port); 
  client.setCallback(callback); 
  udp.begin(udp_port); 

  Wire.begin(SDA_PIN, SCL_PIN); 
  Wire.setClock(400000); 
  
  if (particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("✅ Heart Rate Sensor Found."); 
    particleSensor.setup();
    particleSensor.setPulseAmplitudeRed(0x1F);
    particleSensor.setPulseAmplitudeIR(0x1F);
  }

  pinMode(TFT_BL, OUTPUT); 
  digitalWrite(TFT_BL, HIGH); 
  SPI.begin(TFT_SCLK, -1, TFT_MOSI, TFT_CS); 
  tft.begin(); 
  tft.setRotation(0);
  tft.fillScreen(GC9A01A_BLACK);
  drawBootScreen("READY");

  writeRegister(CTRL1_XL, 0x40); // Init IMU 
  writeRegister(CTRL2_G, 0x40);  

  initMic();
  Serial.println("--- Setup Complete ---");
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection to ");
    Serial.print(target_ip);
    Serial.print("...");
    if (client.connect("ESP32_WatchClient")) { 
      Serial.println(" ✅ Connected!"); 
      client.subscribe("ikimono/screen/alert"); 
      client.subscribe("ikimono/command/mic"); 
    } else {
      Serial.print(" ❌ Failed, rc=");
      Serial.print(client.state());
      Serial.println(" (Retrying in 2s)");
      delay(2000); 
    }
  }
}

// ==================== LOOP ====================
void loop() {
  if (!client.connected()) reconnect(); 
  client.loop(); 

  // 1. Heart Rate Sensing
  long irValue = particleSensor.getIR(); 
  fingerPresent = (irValue > 50000); 
  if (fingerPresent && checkForBeat(irValue)) { 
    long delta = millis() - lastBeat; 
    lastBeat = millis(); 
    if (delta > 0) {
      bpm = 60.0 / (delta / 1000.0); 
      if (bpm > 20 && bpm < 255) { 
        rates[rateSpot++] = (byte)bpm; 
        rateSpot %= RATE_SIZE; 
        avgBpm = 0;
        for (byte i = 0; i < RATE_SIZE; i++) avgBpm += rates[i]; 
        avgBpm /= RATE_SIZE; 
      }
    }
  }

  // 2. IMU Sensing
  readIMU(); 

  // 3. Audio Streaming (Triggered)
  if (isMicActive) {
    streamAudioUDP(); 
  }

  // 4. Display Update
  if (millis() - lastDisplayUpdate >= 250) { 
    lastDisplayUpdate = millis();
    if (abs(avgBpm - lastDrawnBpm) > 1.0 || remoteState != lastRemoteState || !fingerPresent) { 
      drawFaceScreen(avgBpm, fingerPresent);
      lastDrawnBpm = avgBpm; 
      lastRemoteState = remoteState; 
    }
  }

  // 5. Telemetry Output (10Hz)
  if (millis() - lastDataSend >= 100) { 
    lastDataSend = millis();
    char payload[256]; 
    snprintf(payload, sizeof(payload), 
      "{\"timestamp_ms\":%lu,\"ir\":%ld,\"bpm\":%.1f,\"avg_bpm\":%.1f,\"finger\":%d,\"mic_amp\":%d,\"ax\":%d,\"ay\":%d,\"az\":%d}",
      millis(), irValue, bpm, avgBpm, fingerPresent ? 1 : 0, (int)smoothMic, ax, ay, az
    ); 
    client.publish("ikimono/sensors/biometrics", payload); 
  }
}

// ==================== AUDIO UDP ====================
void initMic() {
  i2s_config_t i2s_config = {}; 
  i2s_config.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX); 
  i2s_config.sample_rate = 16000; 
  i2s_config.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT; 
  i2s_config.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT; 
  i2s_config.communication_format = I2S_COMM_FORMAT_STAND_I2S; 
  i2s_config.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1; 
  i2s_config.dma_buf_count = 8; 
  i2s_config.dma_buf_len = 64; 

  i2s_pin_config_t pin_config = {}; 
  pin_config.bck_io_num = I2S_SCK; 
  pin_config.ws_io_num = I2S_WS; 
  pin_config.data_out_num = I2S_PIN_NO_CHANGE; 
  pin_config.data_in_num = I2S_SD; 

  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL); 
  i2s_set_pin(I2S_PORT, &pin_config); 
}

void streamAudioUDP() {
  int32_t i2sBuffer[256]; 
  size_t bytes_read = 0; 
  if (i2s_read(I2S_PORT, &i2sBuffer, sizeof(i2sBuffer), &bytes_read, 0) == ESP_OK && bytes_read > 0) { 
    int samplesRead = bytes_read / 4; 
    int16_t udpBuffer[256]; 
    int32_t currentVol = 0; 
    for (int i = 0; i < samplesRead; i++) {
      udpBuffer[i] = i2sBuffer[i] >> 8; 
      currentVol += abs(udpBuffer[i]); 
    }
    if (samplesRead > 0) smoothMic = 0.9f * smoothMic + 0.1f * (currentVol / samplesRead); 
    udp.beginPacket(target_ip, udp_port); 
    udp.write((const uint8_t*)udpBuffer, samplesRead * 2); 
    udp.endPacket(); 
  }
}

// ==================== HELPERS ====================
void drawBootScreen(const char *msg) {
  tft.fillScreen(GC9A01A_BLACK); 
  tft.setTextColor(GC9A01A_WHITE); 
  tft.setTextSize(2); 
  tft.setCursor(60, 110); 
  tft.print(msg); 
}

void drawFaceScreen(float hr, bool finger) {
  tft.fillScreen(GC9A01A_BLACK); 
  if (!finger) {
    tft.setTextColor(GC9A01A_YELLOW); 
    tft.setTextSize(2); 
    tft.setCursor(45, 105); 
    tft.print("NO FINGER"); 
    return;
  }
  
  uint16_t faceColor = (remoteState == "STRESSED") ? GC9A01A_RED : GC9A01A_GREEN; 
  bool happy = (remoteState == "CALM"); 
  
  tft.fillCircle(120, 110, 70, faceColor); 
  tft.fillCircle(92, 90, 7, GC9A01A_BLACK); 
  tft.fillCircle(148, 90, 7, GC9A01A_BLACK); 
  if (happy) {
    tft.drawCircle(120, 112, 28, GC9A01A_BLACK); 
    tft.fillRect(88, 78, 64, 30, faceColor); 
  } else {
    tft.drawCircle(120, 140, 28, GC9A01A_BLACK); 
    tft.fillRect(88, 140, 64, 28, faceColor); 
  }
  tft.setTextColor(GC9A01A_WHITE); 
  tft.setCursor(72, 205); 
  tft.print((int)hr); tft.print(" BPM"); 
}

void writeRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(IMU_ADDR); 
  Wire.write(reg); 
  Wire.write(value); 
  Wire.endTransmission(); 
}

void readIMU() {
  Wire.beginTransmission(IMU_ADDR); 
  Wire.write(OUTX_L_G); 
  Wire.endTransmission(false); 
  if (Wire.requestFrom(IMU_ADDR, 12) == 12) {
    gx = Wire.read() | (Wire.read() << 8); 
    gy = Wire.read() | (Wire.read() << 8); 
    gz = Wire.read() | (Wire.read() << 8); 
    ax = Wire.read() | (Wire.read() << 8); 
    ay = Wire.read() | (Wire.read() << 8); 
    az = Wire.read() | (Wire.read() << 8); 
  }
}