import paho.mqtt.client as mqtt
import json
import time
import os
import threading
import uuid
from datetime import datetime
import wave
import whisper
from pynput import keyboard
import numpy as np
import math
import socket

from emotion_classifier import AudioEmotionClassifier

# ============================================================================
# CONFIGURATION - UPDATED FOR CLOUD BROKER
# ============================================================================
MQTT_BROKER = "broker.hivemq.com" 
MQTT_PORT = 1883

# Unique topics to match the new ESP32 Cloud Code
MQTT_TOPIC = "sutd/ikimono/mingx/sensors" 
TOPIC_OUT = "sutd/ikimono/mingx/screen"        
TOPIC_MIC_CMD = "sutd/ikimono/mingx/mic"

UDP_IP = "0.0.0.0"
UDP_PORT = 5005

# Paths - USING YOUR EXACT MAC DESKTOP PATHS
LIVE_DATA_FILE = "/Users/mingx/Desktop/3D term4 /frontend_app/public/data/live_biometrics.json"
HISTORY_FILE = "/Users/mingx/Desktop/3D term4 /frontend_app/public/data/emotion_history.json"
THRESHOLDS_FILE = "thresholds.json"

DEFAULT_HR_THRESHOLD = 95
DEBOUNCE_TIME = 15 
MOTION_THRESHOLD_G = 1.5 

class IkimonoBrain:
    def __init__(self):
        self.emotion_history = []
        self.last_audio_trigger = 0
        self.current_state = "CALM"
        self.audio_buffer = bytearray()
        
        self.is_learning_user = False
        self.long_term_hr = []
        self.last_eval_time = 0
        self.EVAL_INTERVAL = 10800 
        self.CONVERGENCE_MARGIN = 2
        
        os.makedirs(os.path.dirname(LIVE_DATA_FILE), exist_ok=True)
        self.load_thresholds()
        
        self.audio_ai = AudioEmotionClassifier("ser_model_weights.h5")
        print("⏳ Loading local Whisper model...")
        self.local_whisper = whisper.load_model("base")
        print("✅ Whisper loaded successfully!")
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.setup_keyboard_trigger()

    def load_thresholds(self):
        if os.path.exists(THRESHOLDS_FILE):
            try:
                with open(THRESHOLDS_FILE, "r") as f:
                    data = json.load(f)
                    self.hr_threshold = data.get("hr_threshold", DEFAULT_HR_THRESHOLD)
                print(f"⚙️ Loaded Calibrated Thresholds: HR>{self.hr_threshold}")
            except Exception:
                self.revert_to_default_thresholds()
        else:
            self.revert_to_default_thresholds()

    def revert_to_default_thresholds(self):
        self.hr_threshold = DEFAULT_HR_THRESHOLD
        print(f"⚙️ Using Default Thresholds: HR>{self.hr_threshold}")

    def setup_keyboard_trigger(self):
        def on_press(key):
            try:
                if hasattr(key, 'char'):
                    if key.char == 'S': 
                        print("\n⌨️ OVERRIDE: Forcing AI Capture...")
                        self.evaluate_stress(110) 
                    elif key.char == 'R':
                        print("\n🔄 SYSTEM RESET: Wiping data for next user...")
                        self.reset_system()
                    elif key.char == 'C':
                        if not self.is_learning_user:
                            print("\n🚀 Initiating Long-Term Adaptive Calibration...")
                            self.is_learning_user = True
                            self.long_term_hr = []
                            self.last_eval_time = time.time()
            except AttributeError:
                pass
        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        print("⌨️ Shortcuts Active: 'Shift+S' (Stress) | 'Shift+R' (Reset) | 'Shift+C' (Calibrate)")

    def reset_system(self):
        self.emotion_history = []
        self.current_state = "CALM"
        self.last_audio_trigger = 0
        self.audio_buffer.clear()
        self.is_learning_user = False
        with open(HISTORY_FILE, "w") as f: json.dump([], f)
        self.update_live_dashboard(0, 0)
        self.revert_to_default_thresholds()
        if os.path.exists(THRESHOLDS_FILE): os.remove(THRESHOLDS_FILE)
        self.client.publish(TOPIC_OUT, "CALM")

    def evaluate_long_term_profile(self):
        if not self.long_term_hr: return 
        new_hr_base = int(np.mean(self.long_term_hr))
        new_hr_threshold = new_hr_base + 15
        hr_diff = abs(self.hr_threshold - new_hr_threshold)
        self.hr_threshold = new_hr_threshold
        if hr_diff <= self.CONVERGENCE_MARGIN:
            self.is_learning_user = False
            with open(THRESHOLDS_FILE, "w") as f: json.dump({"hr_threshold": self.hr_threshold}, f)
        else:
            self.long_term_hr = []
            self.last_eval_time = time.time()

    def start_udp_listener(self):
        def listen():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((UDP_IP, UDP_PORT))
            print(f"🎧 UDP Audio Listener Active on port {UDP_PORT}")
            while True:
                data, _ = sock.recvfrom(2048)
                self.audio_buffer.extend(data)
                # Keep buffer at max 10 seconds of 16kHz 16-bit audio
                if len(self.audio_buffer) > 320000:
                    self.audio_buffer = self.audio_buffer[-320000:]
        threading.Thread(target=listen, daemon=True).start()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("✅ Brain Connected to HiveMQ Cloud Broker")
            self.client.subscribe(MQTT_TOPIC)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            hr = payload.get("avg_bpm", 70)
            
            # Print to terminal so you know it's working
            print(f"📥 Received Data from Watch | HR: {hr} BPM") 
            
            ax = payload.get("ax", 0)
            ay = payload.get("ay", 0)
            az = payload.get("az", 0)
            
            motion_magnitude = math.sqrt(ax**2 + ay**2 + az**2) / 16384.0
            is_moving = motion_magnitude > MOTION_THRESHOLD_G
            
            if self.is_learning_user:
                self.long_term_hr.append(hr)
                if time.time() - self.last_eval_time >= self.EVAL_INTERVAL:
                    self.evaluate_long_term_profile()
            
            if hr > self.hr_threshold and not is_moving:
                self.evaluate_stress(hr)
            else:
                if time.time() - self.last_audio_trigger > DEBOUNCE_TIME:
                    self.set_state("LEARNING..." if self.is_learning_user else "CALM")
                    
            self.update_live_dashboard(hr, 0) 
            
        except Exception as e:
            # This will show us exactly why it fails to save to your frontend folder
            print(f"❌ ERROR processing message: {e}")

    def evaluate_stress(self, hr):
        current_time = time.time()
        if current_time - self.last_audio_trigger < DEBOUNCE_TIME: return 
            
        self.last_audio_trigger = current_time
        # Start recording in a background thread so the dashboard doesn't freeze
        threading.Thread(target=self._capture_and_analyze_audio, args=(hr,), daemon=True).start()

    def _capture_and_analyze_audio(self, hr):
        print("\n⚠️ SPIKE DETECTED! Commanding watch to open microphone...")
        self.client.publish(TOPIC_MIC_CMD, "ON")
        self.audio_buffer.clear() # Clear out any old audio
        
        print("🎙️ Recording 5 seconds of audio from the watch...")
        time.sleep(5) 
        
        print("🛑 Closing watch microphone. Running AI Analysis...")
        self.client.publish(TOPIC_MIC_CMD, "OFF")
        
        my_audio_bytes = bytes(self.audio_buffer)

        audio_array = np.frombuffer(my_audio_bytes, dtype=np.int16)
        boosted_array = np.clip(audio_array.astype(np.int32) * 3, -32768, 32767).astype(np.int16)
        my_audio_bytes = boosted_array.tobytes()
        
        if len(my_audio_bytes) < 5000:
            print("❌ Insufficient audio data received. Try again.")
            # Trigger stress state anyway for showcase purposes if HR is high
            if hr > self.hr_threshold:
                self.set_state("STRESSED")
                self.log_to_history("NO_AUDIO_TRIGGER", hr, "Audio UDP Blocked by Network")
            return

        raw_emotion = self.audio_ai.predict_emotion(my_audio_bytes)
        print(f"🤖 AI Emotion: {raw_emotion}")
        
        transcript_text = "[Analysis in progress]"
        try:
            temp_filename = "temp_capture.wav"
            with wave.open(temp_filename, 'wb') as wav_file:
                wav_file.setnchannels(1)       
                wav_file.setsampwidth(2)       
                wav_file.setframerate(16000)   
                wav_file.writeframes(my_audio_bytes)
            
            result = self.local_whisper.transcribe(temp_filename)
            transcript_text = result["text"].strip()
            print(f"📝 Transcript: {transcript_text}")
            if os.path.exists(temp_filename): os.remove(temp_filename)
        except Exception:
            pass

        stress_indicators = ["angry", "fearful", "disgust", "sad", "surprised"]
        if raw_emotion in stress_indicators or hr > 100: 
            self.set_state("STRESSED")
            self.log_to_history(raw_emotion, hr, transcript_text)

    def set_state(self, state):
        if self.current_state != state:
            self.current_state = state
            self.client.publish(TOPIC_OUT, state)
            print(f"📡 State: {state}")

    def update_live_dashboard(self, hr, gsr):
        data = {"heart_rate": hr, "gsr": gsr, "emotion_state": self.current_state, "activity": 0.1}
        with open(LIVE_DATA_FILE, "w") as f: json.dump(data, f)

    def log_to_history(self, kaggle_emotion, hr, transcript):
        event = {
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S %p"),
            "emotion": "STRESSED",
            "label": kaggle_emotion.upper(), 
            "avgHR": hr,
            "avgGSR": 0,
            "avgIMU": 0.5,
            "transcript": transcript if transcript else "..."
        }
        self.emotion_history.append(event)
        with open(HISTORY_FILE, "w") as f: json.dump(self.emotion_history, f)

    def start(self):
        self.start_udp_listener()
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            print("🧠 IKIMONO Brain Online. Ready for showcase!")
            self.client.loop_forever()
        except Exception as e:
            print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    brain = IkimonoBrain()
    brain.start()