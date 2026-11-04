"""
Jam TTS & Audio Persona Engine
Delhi Indian Accent, Sweet Female / Male Voice Switcher, Native Hindi/English pronunciation of 'Shahid Sir'.
100% Free: Uses gTTS (Google Indian Neural Voice) + Pygame + Pyttsx3 offline fallback.
"""

import sys
import os
import json
import hashlib
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = REPO_ROOT / "config" / "voice_config.json"
CACHE_DIR = REPO_ROOT / ".cache_audio"
CACHE_DIR.mkdir(exist_ok=True)

# Default Config
DEFAULT_CONFIG = {
    "voice_gender": "female",
    "user_name": "Shahid",
    "honorific": "Sir",
    "accent": "delhi-in",
    "wake_sound": True,
    "energy_threshold": 300
}

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

current_config = load_config()

# Initialize Pygame Mixer for sound playback
pygame_initialized = False
try:
    import pygame
    pygame.mixer.init()
    pygame_initialized = True
except Exception as e:
    print(f"[Notice] Pygame mixer init warning: {e}")

# Initialize Offline Pyttsx3 as backup
pyttsx_engine = None
try:
    import pyttsx3
    pyttsx_engine = pyttsx3.init()
    pyttsx_engine.setProperty('rate', 185)
    pyttsx_engine.setProperty('volume', 0.95)
except Exception:
    pass

def play_audio_file(file_path: Path):
    """Play audio file via pygame mixer without locking the file."""
    if not pygame_initialized or not file_path.exists():
        return
    try:
        sound = pygame.mixer.Sound(str(file_path))
        channel = sound.play()
        while channel.get_busy():
            pygame.time.wait(30)
    except Exception as e:
        print(f"[Audio Playback Error: {e}]")

def play_wake_chime():
    """Play a pleasant, crisp rising double-beep when 'Hey Jam' is heard."""
    if not current_config.get("wake_sound", True):
        return
    try:
        import winsound
        winsound.Beep(950, 70)
        winsound.Beep(1400, 100)
    except Exception:
        pass

def speak_offline_fallback(text: str):
    """Fallback offline TTS via pyttsx3."""
    if not pyttsx_engine:
        return
    gender = current_config.get("voice_gender", "female")
    voices = pyttsx_engine.getProperty('voices')
    for v in voices:
        if gender == "female" and "zira" in v.name.lower():
            pyttsx_engine.setProperty('voice', v.id)
            break
        elif gender == "male" and "david" in v.name.lower():
            pyttsx_engine.setProperty('voice', v.id)
            break
    pyttsx_engine.say(text)
    pyttsx_engine.runAndWait()

def speak(text: str, cache_key: str | None = None, wait: bool = True):
    """
    Speak text with Delhi Indian accent (Sweet Female by default, or Male).
    Uses pre-cached audio when available for 0ms instantaneous response.
    """
    gender = current_config.get("voice_gender", "female")
    print(f"\n🎙️  Jam: {text}")

    # Check cache first
    if cache_key:
        cached_file = CACHE_DIR / f"{cache_key}_{gender}.mp3"
        if cached_file.exists():
            play_audio_file(cached_file)
            return

    # Check md5 hash cache for arbitrary repeated text
    text_hash = hashlib.md5(f"{text}_{gender}".encode('utf-8')).hexdigest()[:12]
    hashed_file = CACHE_DIR / f"dyn_{text_hash}.mp3"
    if hashed_file.exists():
        play_audio_file(hashed_file)
        return

    # Male Voice preference: use pyttsx3 David if set to male
    if gender == "male":
        speak_offline_fallback(text)
        return

    # Female Voice preference (Sweet Delhi Indian accent via gTTS)
    try:
        from gtts import gTTS
        tts = gTTS(text, lang='hi')
        tts.save(str(hashed_file))
        play_audio_file(hashed_file)
    except Exception as e:
        # Network unavailable -> Fallback to local pyttsx3
        speak_offline_fallback(text)

def set_voice_gender(gender: str):
    """Switch voice gender ('female' or 'male') and persist."""
    g = gender.lower().strip()
    if g not in ["female", "male"]:
        return
    current_config["voice_gender"] = g
    save_config(current_config)
    if g == "female":
        speak("Ji Shahid Sir, maine apni awaaz sweet female voice me set kar di hai.", cache_key="switch_female")
    else:
        speak("Ji Shahid Sir, ab se main male voice me baat karunga.", cache_key="switch_male")

def get_voice_gender() -> str:
    return current_config.get("voice_gender", "female")
