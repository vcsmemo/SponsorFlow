import json
import time
import os
import config
from openai import OpenAI
import database
import hashlib

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
To support high-quality brand matching, we need premium, reputable creators:
- 15 high-quality, popular or mid-tail YouTube channels focused heavily on Artificial Intelligence (AI/ML builders, agents, prompt engineers), Tech Entrepreneurship (SaaS founders, indie hackers, startup operators), or Investing & Venture Capital (finance trends, tech investing, stock/crypto analysis) whose names start with the letters: {letters_yt}. (e.g. if letters are A, B, C, then channel names must start with A, B, or C).
- 2 premium Podcasts in the same niches starting with the letters: {letters_pod}.

Format:
{{
  "youtube": [{{"name": "Channel Name", "channel_id": "UC...", "category": "AI/ML" | "Startups" | "Finance" | "Tech"}}],
  "podcasts": [{{"name": "Podcast Name", "rss_url": "https://...", "category": "AI/ML" | "Startups" | "Finance"}}],
}}
IMPORTANT: Make sure channel_id starts with UC and rss_url is a valid podcast RSS feed. 
Prioritize real, existing, high-quality channels that developers, founders, and investors trust.
DO NOT INCLUDE any of these channels (ALREADY ADDED): {avoid_yt}
DO NOT INCLUDE any of these podcasts (ALREADY ADDED): {avoid_pod}
Output ONLY valid JSON.
"""

    response = client.chat.completions.create(
        model=config.KIMI_MODEL,
        messages=[{"role": "system", "content": "You are a data extraction assistant. Output ONLY valid JSON."},
                  {"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=2048
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
    
    conn = None
    try:
        data = generate_more(yt_names, pod_names)
        new_yt = data.get('youtube', [])
        new_pod = data.get('podcasts', [])
        
        # Deduplicate & write to DB
        conn = database.get_connection()
        added_yt = 0
        for item in new_yt:
            if item.get("name") not in yt_names:
                yt.append(item)
                yt_names.append(item.get("name"))
                added_yt += 1
                
                # Write to DB
                cid = item.get("channel_id")
                raw_url = f"https://youtube.com/channel/{cid}"
                avatar = f"https://api.dicebear.com/7.x/initials/svg?seed={item.get('name')}"
                import random
                followers = random.randint(85, 820) * 1000 # 85k to 820k subs
                try:
                    database.execute_write(conn, 
                        "INSERT INTO channels (id, name, platform, raw_url, avatar_url, followers, country) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (cid, item.get("name"), 'youtube', raw_url, avatar, followers, 'US')
                    )
                except Exception as e:
                    conn.rollback()
                    print(f"Error writing YT creator to DB: {e}")
                
        added_pod = 0
        for item in new_pod:
            if item.get("name") not in pod_names:
                pod.append(item)
                pod_names.append(item.get("name"))
                added_pod += 1
                
                # Write to DB
                rss_url = item.get("rss_url")
                cid = "pod_" + hashlib.md5(rss_url.encode('utf-8')).hexdigest()[:8]
                avatar = f"https://api.dicebear.com/7.x/initials/svg?seed={item.get('name')}"
                import random
                followers = random.randint(15, 140) * 1000 # 15k to 140k listeners
                try:
                    database.execute_write(conn, 
                        "INSERT INTO channels (id, name, platform, raw_url, avatar_url, followers, country) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (cid, item.get("name"), 'podcast', rss_url, avatar, followers, 'US')
                    )
                except Exception as e:
                    conn.rollback()
                    print(f"Error writing Podcast creator to DB: {e}")
                    
        with open(YT_FILE, 'w') as f:
            json.dump(yt, f, indent=2)
        with open(POD_FILE, 'w') as f:
            json.dump(pod, f, indent=2)
            
        print(f"Added {added_yt} YT, {added_pod} Podcasts. Waiting 20 seconds...", flush=True)
    except Exception as e:
        print(f"Error in loop: {e}. Retrying in 20 seconds...", flush=True)
        if conn:
            try:
                conn.rollback()
            except:
                pass
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass
                
    time.sleep(20)
