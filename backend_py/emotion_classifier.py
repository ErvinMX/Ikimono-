import numpy as np
import librosa
from tensorflow import keras
import os

class AudioEmotionClassifier:
    def __init__(self, model_path="trained_model.h5"):
        # The script looks for the model in the same folder as this file
        # If the path is different, you may need to provide the full path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        full_model_path = os.path.join(current_dir, model_path)
        
        print(f"🧠 Loading Hugging Face Model from {full_model_path}...")
        
        if not os.path.exists(full_model_path):
            raise FileNotFoundError(f"Missing {model_path}! Move it to: {current_dir}")
            
        self.model = keras.models.load_model(full_model_path)
        
        # Mapping for JagjeevanAK's RAVDESS-trained model
        self.emotion_map = {
            0: 'neutral',
            1: 'calm',
            2: 'happy',
            3: 'sad',
            4: 'angry',
            5: 'fearful',
            6: 'disgust',
            7: 'surprised'
        }
        print("✅ Model loaded successfully!")

    def extract_features(self, data, sr):
        """Extracts 180 features (40 MFCC + 12 Chroma + 128 Mel)"""
        result = np.array([])
        
        # 1. MFCC (40)
        mfccs = np.mean(librosa.feature.mfcc(y=data, sr=sr, n_mfcc=40).T, axis=0)
        result = np.hstack((result, mfccs))
        
        # 2. Chroma (12)
        stft = np.abs(librosa.stft(data))
        chroma = np.mean(librosa.feature.chroma_stft(S=stft, sr=sr).T, axis=0)
        result = np.hstack((result, chroma))
        
        # 3. Mel Spectrogram (128)
        mel = np.mean(librosa.feature.melspectrogram(y=data, sr=sr).T, axis=0)
        result = np.hstack((result, mel))
        
        return result

    def predict_emotion(self, raw_audio_bytes):
        """Processes raw bytes and returns the classified emotion."""
        try:
            # Convert raw bytes to float array
            audio_data = np.frombuffer(raw_audio_bytes, dtype=np.int16).astype(np.float32)
            
            # Extract features
            features = self.extract_features(audio_data, sr=22050)
            
            # Reshape for Keras (1 sample, 180 features, 1 channel)
            feature_reshaped = features.reshape(1, 180, 1)
            
            predictions = self.model.predict(feature_reshaped, verbose=0)
            predicted_index = np.argmax(predictions)
            
            return self.emotion_map.get(predicted_index, "unknown")

        except Exception as e:
            print(f"❌ ML Error: {e}")
            return "error"