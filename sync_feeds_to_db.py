import json
import hashlib
import database
import random

def get_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

def sync():
    conn = database.get_connection()
    
    # 1. Load YT feeds
    try:
        with open('data/feeds_youtube.json', 'r') as f:
            yt_feeds = json.load(f)
    except Exception as e:
        print("Error loading YT feeds:", e)
        yt_feeds = []
        
    # 2. Load Podcast feeds
    try:
        with open('data/feeds_podcasts.json', 'r') as f:
            pod_feeds = json.load(f)
    except Exception as e:
        print("Error loading Podcast feeds:", e)
        pod_feeds = []

    print(f"Loaded {len(yt_feeds)} YouTube feeds, {len(pod_feeds)} Podcast feeds.")
    
    # Fetch existing channels
    existing_channels = database.execute_query(conn, "SELECT name, raw_url FROM channels")
    existing_urls = set(row['raw_url'].lower() for row in existing_channels)
    existing_names = set(row['name'].lower() for row in existing_channels)
    
    params_list = []
    
    # Process YouTube
    for item in yt_feeds:
        name = item.get("name")
        channel_id = item.get("channel_id")
        if not name or not channel_id:
            continue
            
        raw_url = f"https://youtube.com/channel/{channel_id}"
        if raw_url.lower() in existing_urls or name.lower() in existing_names:
            continue
            
        cid = channel_id if len(channel_id) <= 50 else channel_id[:50]
        avatar = f"https://api.dicebear.com/7.x/initials/svg?seed={name}"
        followers = random.randint(85, 820) * 1000 # 85k to 820k subs
        
        params_list.append((cid, name, 'youtube', raw_url, avatar, followers, 'US'))
        existing_urls.add(raw_url.lower())
        existing_names.add(name.lower())

    # Process Podcasts
    for item in pod_feeds:
        name = item.get("name")
        rss_url = item.get("rss_url")
        if not name or not rss_url:
            continue
            
        if rss_url.lower() in existing_urls or name.lower() in existing_names:
            continue
            
        cid = "pod_" + get_hash(rss_url)
        avatar = f"https://api.dicebear.com/7.x/initials/svg?seed={name}"
        followers = random.randint(15, 140) * 1000 # 15k to 140k listeners
        
        params_list.append((cid, name, 'podcast', rss_url, avatar, followers, 'US'))
        existing_urls.add(rss_url.lower())
        existing_names.add(name.lower())
            
    added_count = 0
    if params_list:
        try:
            database.execute_many(conn, 
                "INSERT INTO channels (id, name, platform, raw_url, avatar_url, followers, country) VALUES (?, ?, ?, ?, ?, ?, ?)",
                params_list
            )
            added_count = len(params_list)
        except Exception as e:
            print("Error executing batch insert:", e)
            
    conn.close()
    print(f"Batch Synced {added_count} new creators into database successfully.")

if __name__ == '__main__':
    sync()
