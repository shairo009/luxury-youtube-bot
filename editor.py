import subprocess
import os
import json
import requests
import random

with open("config.json") as f:
    config = json.load(f)

OUTPUT_DIR = config.get("output_dir", "output")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

def fetch_stock_video(query: str, index: int = 0) -> str:
    """Fetches a vertical luxury video from Pexels."""
    video_path = f"{OUTPUT_DIR}/stock_{index}.mp4"
    
    if not PEXELS_API_KEY:
        print("WARNING: PEXELS_API_KEY not found! Using a fallback static video.")
        # Fallback to a generic open-source video URL if no key is provided
        fallback_url = "https://static.videezy.com/system/resources/previews/000/038/735/original/alb_cityscapes004_1080p_24fps.mp4"
        r = requests.get(fallback_url, stream=True)
        with open(video_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk: f.write(chunk)
        return video_path

    print(f"Searching Pexels for: {query}")
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&size=large&per_page=15"
    headers = {"Authorization": PEXELS_API_KEY}
    
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        raise Exception(f"Pexels API error: {r.status_code} - {r.text}")
        
    data = r.json()
    if not data.get("videos"):
        print(f"No videos found for {query}, falling back to 'luxury'")
        return fetch_stock_video("luxury", index)
        
    # Pick a random video from the top results
    video = random.choice(data["videos"])
    
    # Find the best quality HD video link
    video_files = video.get("video_files", [])
    hd_files = [f for f in video_files if f.get("quality") == "hd" and f.get("width", 0) >= 1080]
    
    if hd_files:
        best_link = hd_files[0]["link"]
    elif video_files:
        best_link = video_files[0]["link"]
    else:
        raise Exception("No valid video files found in Pexels response.")
        
    print(f"Downloading stock video from Pexels...")
    r = requests.get(best_link, stream=True)
    with open(video_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk: f.write(chunk)
            
    print(f"Stock video saved: {video_path}")
    return video_path


def format_video_for_shorts(input_path: str, output_path: str, duration: int = 15) -> str:
    """Crops, scales, and trims the video to 9:16 Shorts format (1080x1920)."""
    # Using crop and scale to ensure it fits 9:16 perfectly without stretching
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-t", str(duration),
        "-vf", "crop=ih*(9/16):ih,scale=1080:1920",
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "fast",
        "-an", # Remove original audio
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Video formatted for Shorts: {output_path}")
    return output_path


def merge_voice_with_video(video_path: str, voice_path: str, output_path: str) -> str:
    """Merges the AI voiceover with the stock video and loops video if voice is longer."""
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", # Loop video if voice is longer
        "-i", video_path,
        "-i", voice_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest", # Stop when the shortest stream (audio) ends
        "-c:v", "copy",
        "-c:a", "aac",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Voice merged: {output_path}")
    return output_path


def create_video(search_query: str, voice_file: str, output_path: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Step 1: Fetching stock video...")
    stock_vid = fetch_stock_video(search_query)

    print("Step 2: Formatting video for YouTube Shorts (9:16)...")
    formatted_vid = f"{OUTPUT_DIR}/formatted_stock.mp4"
    format_video_for_shorts(stock_vid, formatted_vid, duration=30) # Grab up to 30s, will be trimmed by audio later

    print("Step 3: Merging voiceover with video...")
    voiced = f"{OUTPUT_DIR}/final_voiced.mp4"
    merge_voice_with_video(formatted_vid, voice_file, voiced)

    import shutil
    shutil.copy(voiced, output_path)
    print(f"Final Luxury Video ready: {output_path}")
    return output_path

