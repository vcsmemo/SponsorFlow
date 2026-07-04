import json
import time
import os
import config
from openai import OpenAI

config.validate_config("llm")
client = OpenAI(api_key=config.KIMI_API_KEY, base_url=config.KIMI_BASE_URL)

YT_FILE = 'data/feeds_youtube.json'
POD_FILE = 'data/feeds_podcasts.json'

def count_feeds():
    try:
        with open(YT_FILE, 'r') as f:
            yt = json.load(f)
    except: yt = []
    try:
        with open(POD_FILE, 'r') as f:
            pod = json.load(f)
    except: pod = []
    return yt, pod

def generate_more(yt_names, pod_names):
    import random
    import string
    # Select random letters to enforce diversity and prevent duplicate generation
    letters_yt = random.sample(string.ascii_uppercase, 5)
    letters_pod = random.sample(string.ascii_uppercase, 5)
    
    avoid_yt = ", ".join(yt_names[-100:]) if len(yt_names) > 0 else "None"
    avoid_pod = ", ".join(pod_names[-100:]) if len(pod_names) > 0 else "None"
    
    prompt = f"""
Generate a JSON object with two arrays: 'youtube' and 'podcasts'.
To ensure high diversity and discover long-tail creators, we need:
- 5 popular or mid-tail YouTube channels in Tech, Finance, AI, SaaS, or Business whose names start with the letters: {letters_yt}. (e.g. if letters are A, B, C, then channel names must start with A, B, or C).
- 5 popular or mid-tail Podcasts in Tech, Finance, AI, SaaS, or Business whose names start with the letters: {letters_pod}.

Format:
{{
  "youtube": [{{"name": "Channel Name", "channel_id": "UC...", "category": "Tech"}}],
  "podcasts": [{{"name": "Podcast Name", "rss_url": "https://...", "category": "Tech"}}]
}}
IMPORTANT: Make sure channel_id starts with UC and rss_url is a valid podcast RSS feed.
DO NOT INCLUDE any of these channels (ALREADY ADDED): {avoid_yt}
DO NOT INCLUDE any of these podcasts (ALREADY ADDED): {avoid_pod}
Output ONLY valid JSON.
"""

    response = client.chat.completions.create(
        model=config.KIMI_MODEL,
        messages=[{"role": "system", "content": "You are a data extraction assistant. Output ONLY valid JSON."},
                  {"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

while True:
    yt, pod = count_feeds()
    total = len(yt) + len(pod)
    print(f"Current total feeds: {total} ({len(yt)} YT, {len(pod)} Podcasts)", flush=True)
    if total >= 1000:
        print("Reached target of 1000 creators! Exiting.", flush=True)
        break
        
    yt_names = [x.get("name") for x in yt]
    pod_names = [x.get("name") for x in pod]
    
    try:
        data = generate_more(yt_names, pod_names)
        new_yt = data.get('youtube', [])
        new_pod = data.get('podcasts', [])
        
        # Deduplicate
        added_yt = 0
        for item in new_yt:
            if item.get("name") not in yt_names:
                yt.append(item)
                yt_names.append(item.get("name"))
                added_yt += 1
                
        added_pod = 0
        for item in new_pod:
            if item.get("name") not in pod_names:
                pod.append(item)
                pod_names.append(item.get("name"))
                added_pod += 1
                
        with open(YT_FILE, 'w') as f:
            json.dump(yt, f, indent=2)
        with open(POD_FILE, 'w') as f:
            json.dump(pod, f, indent=2)
            
        print(f"Added {added_yt} YT, {added_pod} Podcasts. Waiting 60 seconds...", flush=True)
    except Exception as e:
        print(f"Error fetching from LLM: {e}. Retrying in 60 seconds...", flush=True)
        
    time.sleep(60)
