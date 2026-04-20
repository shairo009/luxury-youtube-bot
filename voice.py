import json
import os
import requests

with open("config.json") as f:
    config = json.load(f)

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", config.get("elevenlabs_api_key", ""))
VOICE_ID = config["elevenlabs_voice_id"]
SETTINGS = config["elevenlabs_settings"]


def generate_voice(text: str, output_path: str) -> str:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": SETTINGS["stability"],
            "similarity_boost": SETTINGS["similarity_boost"],
            "style": SETTINGS["style"],
            "use_speaker_boost": SETTINGS["use_speaker_boost"]
        }
    }

    print(f"Generating voice: {text[:60]}...")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"ElevenLabs error: {response.status_code} - {response.text}")

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(response.content)

    print(f"Voice saved: {output_path}")

    speed = SETTINGS.get("speed", 1.10)
    if speed != 1.0:
        sped_path = output_path.replace(".mp3", "_fast.mp3")
        change_speed(output_path, sped_path, speed)
        return sped_path

    return output_path


def change_speed(input_path: str, output_path: str, speed: float = 1.10) -> str:
    import subprocess
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-filter:a", f"atempo={speed}",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Speed adjusted ({speed}x): {output_path}")
    return output_path
