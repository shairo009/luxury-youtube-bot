import subprocess
import os
import json
import requests

with open("config.json") as f:
    config = json.load(f)

STOCKFISH_PATH = "stockfish"
OUTPUT_DIR = config.get("output_dir", "output")


def fetch_board_gif(game_id: str, blunder_index: int) -> str:
    gif_path = f"{OUTPUT_DIR}/board_{game_id}.gif"
    url = f"https://lichess.org/game/export/gif/{game_id}.gif?theme={config['chess_board_theme']}&piece={config['piece_theme']}"
    r = requests.get(url)
    if r.status_code == 200:
        with open(gif_path, "wb") as f:
            f.write(r.content)
        print(f"Board GIF saved: {gif_path}")
        return gif_path
    else:
        raise Exception(f"Could not fetch board GIF: {r.status_code}")


def convert_gif_to_mp4(gif_path: str, output_path: str) -> str:
    cmd = [
        "ffmpeg", "-y",
        "-i", gif_path,
        "-movflags", "faststart",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"GIF converted to MP4: {output_path}")
    return output_path


def add_zoom_effect(input_path: str, output_path: str, start_sec: int = 5) -> str:
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", (
            f"zoompan=z='if(gte(t,{start_sec}),1.5,1)'"
            f":x='iw/2-(iw/zoom/2)'"
            f":y='ih/2-(ih/zoom/2)'"
            f":d=1:s=1080x1920:fps=30"
        ),
        "-c:a", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Zoom added: {output_path}")
    return output_path


def add_red_box_and_arrow(input_path: str, output_path: str) -> str:
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", (
            "drawbox=x=200:y=200:w=120:h=120:color=red@0.8:t=4,"
            "drawtext=text='❌ Blunder':fontcolor=red:fontsize=36:x=200:y=330"
        ),
        "-c:a", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Red box added: {output_path}")
    return output_path


def add_captions(input_path: str, output_path: str, voice_lines: str) -> str:
    srt_path = f"{OUTPUT_DIR}/captions.srt"
    lines = [l.strip() for l in voice_lines.strip().split("\n") if l.strip()]
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, line in enumerate(lines):
            start = i * 2
            end = start + 2
            f.write(f"{i+1}\n")
            f.write(f"00:00:{start:02d},000 --> 00:00:{end:02d},000\n")
            f.write(f"{line}\n\n")

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"subtitles={srt_path}:force_style='Fontsize=24,PrimaryColour=&H00FFFFFF,Bold=1,Outline=2'",
        "-c:a", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Captions added: {output_path}")
    return output_path


def merge_voice_with_video(video_path: str, voice_path: str, output_path: str) -> str:
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", voice_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-c:v", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Voice merged: {output_path}")
    return output_path


def add_background_music(video_path: str, music_path: str, output_path: str) -> str:
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", music_path,
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=shortest:weights=1 0.15[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Background music added: {output_path}")
    return output_path


def trim_clip(input_path: str, output_path: str, duration: int = 10) -> str:
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-t", str(duration),
        "-c", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Clip trimmed to {duration}s: {output_path}")
    return output_path


def create_video(
    game_id: str,
    blunder_index: int,
    voice_file: str,
    edit_plan: str,
    output_path: str
) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    gif = fetch_board_gif(game_id, blunder_index)
    raw_mp4 = f"{OUTPUT_DIR}/raw_{game_id}.mp4"
    convert_gif_to_mp4(gif, raw_mp4)

    trimmed = f"{OUTPUT_DIR}/trimmed_{game_id}.mp4"
    trim_clip(raw_mp4, trimmed, duration=10)

    zoomed = f"{OUTPUT_DIR}/zoomed_{game_id}.mp4"
    add_zoom_effect(trimmed, zoomed)

    boxed = f"{OUTPUT_DIR}/boxed_{game_id}.mp4"
    add_red_box_and_arrow(zoomed, boxed)

    voiced = f"{OUTPUT_DIR}/voiced_{game_id}.mp4"
    merge_voice_with_video(boxed, voice_file, voiced)

    captioned = f"{OUTPUT_DIR}/captioned_{game_id}.mp4"
    add_captions(voiced, captioned, voice_lines=edit_plan)

    import shutil
    shutil.copy(captioned, output_path)
    print(f"Final video ready: {output_path}")
    return output_path
