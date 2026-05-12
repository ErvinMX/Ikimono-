# Emotion Detection System - Brain (PC Backend)

Complete Python backend for processing wearable biometric and audio data to detect emotional states.

## 🏗️ System Architecture

```
┌─────────────────┐         MQTT          ┌──────────────────┐
│  ESP32 Wristband│ ───► biometrics ───► │                  │
│  (HR, GSR, Temp)│                        │   PC BRAIN       │
└─────────────────┘                        │  (This Script)   │
                                           │                  │
┌─────────────────┐          UDP          │  - MQTT Client   │
│  ESP32 Mic      │ ───► audio stream ──► │  - UDP Server    │
│  (Raw Audio)    │                        │  - ML Processing │
└─────────────────┘                        └─────────┬────────┘
                                                     │ MQTT
                                                     │ emotion
                                                     ▼
                                           ┌─────────────────┐
                                           │  ESP32 Screen   │
                                           │  (Tamagotchi)   │
                                           └─────────────────┘
```

## 📋 Prerequisites

1. **Mosquitto MQTT Broker** running locally
2. **Python 3.8+**
3. **Network connectivity** between PC and ESP32 devices

## 🚀 Installation

### 1. Install Mosquitto MQTT Broker

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

**macOS:**
```bash
brew install mosquitto
brew services start mosquitto
```

**Windows:**
Download from [mosquitto.org](https://mosquitto.org/download/)

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## 🎮 Usage

### Start the Brain

```bash
python emotion_detection_brain.py
```

You should see:
```
============================================================
EMOTION DETECTION BRAIN - STARTING
============================================================

[MQTT] Connecting to broker at localhost:1883...
[MQTT] Connected successfully to broker at localhost
[MQTT] Subscribed to topic: sensors/biometrics
[UDP] Starting audio listener on 0.0.0.0:5005
[UDP] Listening for audio stream...

[SYSTEM] All systems operational. Press Ctrl+C to stop.
```

## 🧪 Testing

### Test MQTT (Biometric Data)

Open a new terminal and publish test biometric data:

```bash
# Install mosquitto-clients if not already installed
mosquitto_pub -h localhost -t "sensors/biometrics" -m '{"heart_rate": 105, "gsr": 450, "temperature": 36.5}'
```

Expected output in brain console:
```
[MQTT] Received biometrics: {'heart_rate': 105, 'gsr': 450, 'temperature': 36.5}
[BIOMETRICS] HR: 105 BPM | GSR: 450 | Temp: 36.5°C

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
[SPIKE DETECTED] Reasons: High HR (105 BPM)
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

[TRIGGER] Initiating audio emotion evaluation...
[ML MOCK] Running AI emotion evaluation...
[MQTT] Published emotion 'anxious' to device/screen/character
```

### Test UDP (Audio Stream)

Use the provided test script:

```bash
python test_udp_audio.py
```

Or manually with Python:

```python
import socket
import time

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
for i in range(100):
    fake_audio = b'\x00\x01' * 1024  # Fake audio data
    sock.sendto(fake_audio, ('localhost', 5005))
    time.sleep(0.1)
sock.close()
```

### Monitor MQTT Output

Subscribe to the emotion output topic:

```bash
mosquitto_sub -h localhost -t "device/screen/character"
```

You'll receive emotion updates like:
```json
{"emotion": "anxious", "timestamp": "2024-04-10T14:30:45.123456"}
```

## ⚙️ Configuration

Edit the `Config` class in `emotion_detection_brain.py`:

```python
class Config:
    # MQTT Settings
    MQTT_BROKER = "localhost"
    MQTT_PORT = 1883
    MQTT_TOPIC_BIOMETRICS = "sensors/biometrics"
    MQTT_TOPIC_OUTPUT = "device/screen/character"
    
    # UDP Settings
    UDP_PORT = 5005
    AUDIO_BUFFER_SIZE = 4096
    
    # Biometric Thresholds
    HEART_RATE_THRESHOLD = 100  # Adjust based on your needs
    GSR_THRESHOLD = 500
    TEMP_HIGH_THRESHOLD = 37.5
```

## 📊 Expected Data Formats

### MQTT Biometric Input (`sensors/biometrics`)

```json
{
  "heart_rate": 85,
  "gsr": 350,
  "temperature": 36.8
}
```

### MQTT Emotion Output (`device/screen/character`)

```json
{
  "emotion": "calm",
  "timestamp": "2024-04-10T14:30:45.123456"
}
```

### UDP Audio Input

- **Protocol:** UDP
- **Port:** 5005
- **Format:** Raw audio bytes (PCM, WAV, or your chosen format)
- **Chunk Size:** Configurable (default 4096 bytes)

## 🤖 Integrating Real ML Models

The script has a mock function `evaluate_emotion_from_audio()` ready for your ML model.

### Example Whisper + Sentiment Integration

```python
import whisper
from transformers import pipeline

# Initialize models (do this once at startup)
whisper_model = whisper.load_model("base")
sentiment_analyzer = pipeline("sentiment-analysis", 
                             model="distilbert-base-uncased-finetuned-sst-2-english")

def evaluate_emotion_from_audio(audio_chunks: list) -> str:
    # 1. Concatenate audio
    audio_data = b''.join([chunk['data'] for chunk in audio_chunks])
    
    # 2. Save to temp WAV file or convert to numpy array
    with open("temp_audio.wav", "wb") as f:
        # Add WAV header if needed
        f.write(audio_data)
    
    # 3. Transcribe with Whisper
    result = whisper_model.transcribe("temp_audio.wav")
    text = result['text']
    
    # 4. Sentiment analysis
    sentiment = sentiment_analyzer(text)[0]
    
    # 5. Map sentiment to emotion
    emotion_map = {
        'POSITIVE': 'happy',
        'NEGATIVE': 'anxious'
    }
    
    return emotion_map.get(sentiment['label'], 'calm')
```

Then uncomment the ML dependencies in `requirements.txt` and install:

```bash
pip install openai-whisper transformers torch librosa
```

## 🔧 Troubleshooting

### MQTT Connection Failed

```bash
# Check if Mosquitto is running
sudo systemctl status mosquitto

# Test with mosquitto_pub
mosquitto_pub -h localhost -t test -m "hello"
```

### UDP Not Receiving Data

- Verify the ESP32 is sending to the correct IP address of your PC
- Check firewall rules:
  ```bash
  # Ubuntu/Linux
  sudo ufw allow 5005/udp
  ```
- Use Wireshark to verify UDP packets are arriving

### Import Errors

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

## 📁 File Structure

```
emotion-detection-brain/
│
├── emotion_detection_brain.py    # Main script
├── requirements.txt               # Python dependencies
├── test_udp_audio.py             # UDP testing script
└── README.md                     # This file
```

## 🛣️ Next Steps

1. ✅ Test with actual ESP32 devices
2. ✅ Integrate real ML models (Whisper, sentiment analysis)
3. ✅ Add data logging/persistence
4. ✅ Implement emotion smoothing/filtering
5. ✅ Add web dashboard for monitoring
6. ✅ Implement user calibration for thresholds

## 📝 License

MIT License - Feel free to modify and use in your projects!

## 🙋 Support

For issues or questions, refer to the inline code comments or create an issue in your project repository.
