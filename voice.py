import os
from gtts import gTTS

def generate_voice(text: str, output_path: str, voice_id: str = None, api_key: str = None) -> str:
    # We switch to gTTS because it's the most reliable on GitHub Actions.
    # It's free and always works.
    
    print(f"Generating voice (gTTS): {text[:60]}...")
    
    # Using 'hi' (Hindi) with 'en' (English) accent works well for Hinglish.
    # Or just 'en' with Indian accent.
    tts = gTTS(text=text, lang='en', tld='co.in') 
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    tts.save(output_path)
    
    print(f"Voice saved: {output_path}")
    return output_path
