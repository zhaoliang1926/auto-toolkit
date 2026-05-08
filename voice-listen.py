#!/usr/bin/env python3
"""
Voice chat with wake word. Says '星河' to activate, then speak your message.
Voiceprint protection via resemblyzer.
"""
import subprocess
import os
import sys
import time
import json
from datetime import datetime
import speech_recognition as sr

VOICE_DIR = os.path.expanduser("~/.claude/voice-chat")
INBOX = os.path.join(VOICE_DIR, "inbox.txt")
VOICEPRINT_FILE = os.path.join(VOICE_DIR, "voiceprint.json")
MUTE_FILE = os.path.join(VOICE_DIR, "mute_until")
os.makedirs(VOICE_DIR, exist_ok=True)

WAKE_WORD = "星河"
LISTEN_CLIP = 5   # seconds per clip during wake-word detection
MSG_CLIP = 15     # seconds to record after wake word

# ---- Voiceprint ----
def has_resemblyzer():
    try: import resemblyzer; return True
    except: return False

def enroll_voiceprint(audiofile):
    from resemblyzer import VoiceEncoder, preprocess_wav
    encoder = VoiceEncoder()
    wav = preprocess_wav(audiofile)
    if len(wav) < 16000: return None
    embedding = encoder.embed_utterance(wav)
    with open(VOICEPRINT_FILE, "w") as f:
        json.dump(embedding.tolist(), f)
    return embedding

def load_voiceprint():
    if not os.path.exists(VOICEPRINT_FILE): return None
    with open(VOICEPRINT_FILE) as f: return json.load(f)

def verify_voice(audiofile):
    enrolled = load_voiceprint()
    if enrolled is None or not has_resemblyzer(): return True
    from resemblyzer import VoiceEncoder, preprocess_wav
    import numpy as np
    encoder = VoiceEncoder()
    wav = preprocess_wav(audiofile)
    if len(wav) < 16000: return False
    emb = encoder.embed_utterance(wav)
    return float(np.dot(enrolled, emb)) > 0.75

# ---- Recording ----
def record_clip(seconds):
    audiofile = os.path.join(VOICE_DIR, f"clip_{int(time.time())}.wav")
    cmd = ["rec", "-r", "16000", "-c", "1", "-b", "16", "-e", "signed-integer",
           audiofile, "trim", "0", str(seconds)]
    try:
        subprocess.run(cmd, timeout=seconds + 5, capture_output=True)
        if os.path.exists(audiofile) and os.path.getsize(audiofile) > 2000:
            return audiofile
    except: pass
    if os.path.exists(audiofile): os.remove(audiofile)
    return None

# ---- Transcription ----
def transcribe(audiofile):
    r = sr.Recognizer()
    try:
        with sr.AudioFile(audiofile) as source:
            audio = r.record(source)
        return r.recognize_google(audio, language='zh-CN')
    except: return None

# ---- TTS ----
def speak(text):
    # Speak, then mute mic for 3 seconds to avoid echo
    subprocess.run(["say", "-v", "Tingting", text])
    with open(MUTE_FILE, "w") as f:
        f.write(str(time.time() + 3))

def is_muted():
    try:
        with open(MUTE_FILE) as f:
            return time.time() < float(f.read().strip())
    except: return False

def main():
    print(f"Wake word: '{WAKE_WORD}'")
    print(f"Say '{WAKE_WORD}' then speak your message.")
    if has_resemblyzer():
        if not load_voiceprint():
            print("No voiceprint. Say '星河 注册声纹' to enroll.")
        else:
            print("Voiceprint active.")
    print("(Ctrl+C to stop)\n")

    login_attempts = 0

    while True:
        try:
            # Skip if muted (after TTS to avoid echo)
            if is_muted():
                time.sleep(0.5)
                continue

            # Phase 1: Listen for wake word
            print("[听]", end="", flush=True)
            clip = record_clip(LISTEN_CLIP)
            if not clip:
                time.sleep(1)
                continue

            text = transcribe(clip)
            os.remove(clip)

            if not text:
                time.sleep(1)
                continue

            # Check for wake word
            if WAKE_WORD not in text:
                time.sleep(1)
                continue

            # Voiceprint check
            if has_resemblyzer() and load_voiceprint() is not None:
                # Re-record for voiceprint check
                vp_clip = record_clip(3)
                if not vp_clip or not verify_voice(vp_clip):
                    login_attempts += 1
                    if vp_clip: os.remove(vp_clip)
                    if login_attempts >= 3:
                        speak("你不是主人，我不理你")
                        time.sleep(5)
                        login_attempts = 0
                    continue
                if vp_clip: os.remove(vp_clip)
                login_attempts = 0

            # If wake word is the whole message (e.g. "星河" or "星河 注册声纹")
            msg = text.replace(WAKE_WORD, "").strip()

            # Phase 2: If message already complete in wake clip, use it
            if len(msg) > 3:
                pass  # Message captured in wake clip
            else:
                # Phase 2: Record the actual message
                speak("请说")
                print("[录]", end="", flush=True)
                msg_clip = record_clip(MSG_CLIP)
                if not msg_clip:
                    continue
                msg = transcribe(msg_clip) or ""
                os.remove(msg_clip)

            if not msg or len(msg) < 2:
                speak("没听清，请再说一次")
                continue

            # Handle enrollment
            if "注册声纹" in msg and has_resemblyzer():
                speak("正在注册声纹，请说一句话")
                print("[注册]", end="", flush=True)
                enroll_file = record_clip(5)
                if enroll_file and enroll_voiceprint(enroll_file) is not None:
                    print("\n  Voiceprint enrolled!", flush=True)
                    speak("声纹注册成功。以后只有你的声音能唤醒我。")
                if enroll_file: os.remove(enroll_file)
                continue

            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n>> [{timestamp}] {msg}", flush=True)

            # Write to inbox for Claude to read
            with open(INBOX, "a") as f:
                f.write(f"[{timestamp}] {msg}\n")

            speak("收到")

        except KeyboardInterrupt:
            print("\nVoice listener stopped.")
            break
        except Exception as e:
            print(f"E: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
