import paho.mqtt.client as mqtt
import json
import time
import socket
import random

# MATCHING THE BRAIN CONFIG
MQTT_BROKER = "localhost"
MQTT_TOPIC = "ikimono/sensors/biometrics"
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

print("🚀 Starting IKIMONO Hardware Simulator...")

# Update to Version 2 to remove the warning
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_BROKER, 1883, 60)
print("🔋 Biometric Core (MQTT) Connected...")

# Setup UDP for "Fake Audio"
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print("🎤 Audio Core (UDP) Broadcasting on port 5005...")

try:
    while True:
        # 1. Send Fake Biometrics
        data = {
            "heart_rate": random.randint(70, 110), # Will occasionally trigger the AI!
            "gsr": random.randint(200, 600)
        }
        client.publish(MQTT_TOPIC, json.dumps(data))
        
        # 2. Send Fake Audio "Noise"
        fake_audio = bytes([random.randint(0, 255) for _ in range(1024)])
        sock.sendto(fake_audio, (UDP_IP, UDP_PORT))
        
        time.sleep(1) # Send every second
except KeyboardInterrupt:
    print("\n🛑 Simulator Stopped.")