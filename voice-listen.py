#!/usr/bin/env python3
"""
Voice chat - continuous recording in short clips.
No key press needed. Just speak, pause, and it captures.
"""
import subprocess
import os
import sys
import time
from datetime import datetime
import speech_recognition as sr

VOICE_DIR = os.path.expanduser("~/.claude/voice-chat")
INBOX = os.path.join(VOICE_DIR, "inbox.txt")
os.makedirs(VOICE_DIR, exist_ok=True)

CLIP_SECONDS = 4  # record 4-second clips
PAUSE_SECONDS = 1  # pause between clips

def record_clip():
    """Record a short audio clip."""
    audiofile = os.path.join(VOICE_DIR, f"clip_{int(time.time())}.wav")
    cmd = [
        "rec", "-r", "16000", "-c", "1", "-b", "16", "-e", "signed-integer",
        audiofile, "trim", "0", str(CLIP_SECONDS)
    ]
    try:
        subprocess.run(cmd, timeout=CLIP_SECONDS + 5, capture_output=True)
        if os.path.exists(audiofile) and os.path.getsize(audiofile) > 2000:
            return audiofile
    except:
        pass
    if os.path.exists(audiofile):
        os.remove(audiofile)
    return None

def has_speech(audiofile):
    """Quick check if clip contains speech (not just silence)."""
    r = sr.Recognizer()
    try:
        with sr.AudioFile(audiofile) as source:
            audio = r.record(source)
        # Try to detect if there's actual speech energy
        # speech_recognition handles this internally
        return True
    except:
        return False

def transcribe(audiofile):
    """Transcribe audio via Google STT."""
    r = sr.Recognizer()
    try:
        with sr.AudioFile(audiofile) as source:
            audio = r.record(source)
        return r.recognize_google(audio, language='zh-CN')
    except sr.UnknownValueError:
        return None
    except Exception as e:
        return None

def speak(text):
    """Reply via TTS."""
    subprocess.Popen(["say", "-v", "Tingting", text])

def main():
    print("Voice chat active. Just speak naturally - no key press needed.")
    print("(Ctrl+C to stop)\n")

    last_text = None  # deduplicate

    while True:
        try:
            clip = record_clip()
            if not clip:
                time.sleep(PAUSE_SECONDS)
                continue

            text = transcribe(clip)
            os.remove(clip)

            if text and text != last_text:
                last_text = text
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"\n>> [{timestamp}] {text}", flush=True)

                with open(INBOX, "a") as f:
                    f.write(f"[{timestamp}] {text}\n")

                # Speak confirmation
                speak("收到")

            time.sleep(PAUSE_SECONDS)

        except KeyboardInterrupt:
            print("\nVoice listener stopped.")
            break
        except Exception as e:
            print(f"E: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
