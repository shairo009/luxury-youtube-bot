import json
import os
import random
import sys
import time
import requests
from dotenv import load_dotenv
from voice import generate_voice
from editor import create_video
from uploader import upload_to_youtube

load_dotenv()

with open("config.json") as f:
    config = json.load(f)

with open("prompt.txt") as f:
    PROMPT_TEMPLATE = f.read()

TONES = [
    "Toxic Pro 🎮", "Hacker Mind 🧠", "Funny Noob 😂", "Sigma Rule 🗿", 
    "Drama King 🎭", "Rage Master 😡", "Chill Pro 😎", "Evil Genius 😈", 
    "Memer 🤡", "Desi Gamer 🇮🇳"
]

OPENROUTER_API_KEY  = os.environ.get("OPENROUTER_API_KEY", "")
ELEVENLABS_API_KEY  = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", config.get("elevenlabs_voice_id", ""))
YOUTUBE_CHANNEL_ID  = os.environ.get("YOUTUBE_CHANNEL_ID", config.get("youtube_channel_id", ""))

# Famous top Lichess players - zero touch, random pick
TOP_PLAYERS = [
    "DrNykterstein",   # Magnus Carlsen
    "nihalsarin",      # Nihal Sarin
    "DanielNaroditsky",
    "penguingim1",     # Andrew Tang
    "alireza2003",     # Alireza Firouzja
    "RebeccaHarris",   # Hikaru (one of his accounts)
    "LyonBeast",
    "Zhigalko_Sergei",
    "Baskaran_Adhiban",
    "rpragchess",      # Praggnanandhaa
    "vincentkeymer",
    "mishanick",
    "Firouzja2003",
]


def fetch_top_player_game():
    # Try multiple players until we find one with valid games
    shuffled_players = TOP_PLAYERS.copy()
    random.shuffle(shuffled_players)
    
    for player in shuffled_players:
        try:
            print(f"Fetching games from top player: {player}")
            url = f"https://lichess.org/api/games/user/{player}?max=50&analysed=true&evals=true&perfType=bullet,blitz"
            headers = {"Accept": "application/x-ndjson"}
            r = requests.get(url, headers=headers, stream=True, timeout=15)
            
            games = []
            for line in r.iter_lines():
                if line:
                    try:
                        games.append(json.loads(line))
                    except Exception:
                        pass
            
            if games:
                print(f"Found {len(games)} games from {player}")
                return random.choice(games), player
            else:
                print(f"No analysed games found for {player}, trying next...")
        except Exception as e:
            print(f"Error fetching from {player}: {e}")
            
    raise Exception("Could not find any analysed games for any of the top players.")


def extract_blunder(game):
    analysis = game.get("analysis", [])
    blunders = []
    for i, move in enumerate(analysis):
        if move.get("judgment", {}).get("name") in ["Blunder", "Mistake"]:
            blunders.append((i, move))
    if not blunders:
        return None
    blunder_index, blunder_move = random.choice(blunders)
    return {
        "pgn": game.get("pgn", ""),
        "blunder_move": blunder_move,
        "blunder_index": blunder_index,
        "game_id": game.get("id", "unknown"),
        "players": game.get("players", {})
    }


def call_openrouter(prompt, tone, player):
    model = config.get("openrouter_model", "mistralai/mistral-7b-instruct:free")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/shairo009/human-chess-bot-yt",
        "X-Title": "Human Chess Bot YT"
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a human YouTube Shorts chess creator. "
                    "Use Hinglish (Hindi + English mix). "
                    "Respond ONLY in the exact OUTPUT format given, nothing else."
                )
            },
            {
                "role": "user",
                "content": (
                    prompt
                    + f"\n\nTone for this video: {tone}"
                    + f"\nThis blunder is from a game by top player: {player}"
                )
            }
        ],
        "temperature": 0.9,
        "max_tokens": 500
    }
    print(f"Calling OpenRouter ({model})...")
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    if r.status_code != 200:
        raise Exception(f"OpenRouter error {r.status_code}: {r.text}")
    return r.json()["choices"][0]["message"]["content"]


def parse_script(raw):
    result = {}
    current_key = None
    for line in raw.strip().split("\n"):
        matched = False
        for key in ["HOOK", "VOICE_LINES", "STYLE", "TITLE", "DESCRIPTION", "HASHTAGS", "EDIT_PLAN"]:
            if line.startswith(f"{key}:"):
                current_key = key
                result[key] = line[len(key)+1:].strip()
                matched = True
                break
        if not matched and current_key and line.strip():
            result[current_key] = result.get(current_key, "") + "\n" + line.strip()
    return result


def make_one_video(index=0):
    tone = random.choice(TONES)
    print(f"\nTone selected: {tone}")

    blunder = None
    player = None
    while not blunder:
        game, player = fetch_top_player_game()
        blunder = extract_blunder(game)
        if not blunder:
            print("No blunder found in this game, retrying with another...")

    print(f"Game: {blunder['game_id']} | Blunder at move: {blunder['blunder_index']} | Player: {player}")

    raw_script = call_openrouter(PROMPT_TEMPLATE, tone, player)
    script = parse_script(raw_script)
    print("Script:\n", json.dumps(script, indent=2, ensure_ascii=False))

    voice_file = generate_voice(
        text=script.get("HOOK", "") + " " + script.get("VOICE_LINES", ""),
        output_path=f"output/voice_{index}.mp3",
        voice_id=ELEVENLABS_VOICE_ID,
        api_key=ELEVENLABS_API_KEY
    )

    print(f"Generating video for Game: {blunder['game_id']}...")
    video_file = create_video(
        game_id=blunder["game_id"],
        blunder_index=blunder["blunder_index"],
        voice_file=voice_file,
        edit_plan=script.get("EDIT_PLAN", ""),
        output_path=f"output/video_{index}.mp4"
    )
    print(f"Video created: {video_file}")

    # Metadata Jitter: Randomize emojis and symbols to look human
    random_emojis = ["♟️", "🔥", "😱", "💀", "👑", "🚀", "💥", "🤖"]
    jitter = random.choice(random_emojis) + " " + random.choice(random_emojis)
    
    final_title = f"{script.get('TITLE', 'Chess Blunder')} {jitter}"[:100]
    
    if "--no-upload" in sys.argv:
        print(f"Skipping upload for video {index+1} (--no-upload is set).")
    else:
        upload_to_youtube(
            video_path=video_file,
            title=final_title,
            description=script.get("DESCRIPTION", "") + "\n\n" + script.get("HASHTAGS", "") + "\n\n#Chess #Shorts #Automation",
            tags=script.get("HASHTAGS", "").replace("#", "").split()
        )
        print(f"Video {index+1} uploaded successfully!")


def run_all():
    videos_per_day = config.get("videos_per_day", 4)
    gap_hours = config.get("gap_hours", 3)
    for i in range(videos_per_day):
        print(f"\n=== Video {i+1}/{videos_per_day} ===")
        try:
            make_one_video(i)
        except Exception as e:
            print(f"Error on video {i+1}: {e}")
        if i < videos_per_day - 1:
            print(f"Waiting {gap_hours}h...")
            time.sleep(gap_hours * 3600)


if __name__ == "__main__":
    if "--single" in sys.argv:
        # Retry up to 3 times for a single video in case of transient API errors (like Lichess GIF 404)
        for attempt in range(3):
            try:
                make_one_video(index=int(time.time()) % 10000)
                break
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt == 2:
                    raise e
                print("Retrying in 10 seconds...")
                time.sleep(10)
    else:
        run_all()
