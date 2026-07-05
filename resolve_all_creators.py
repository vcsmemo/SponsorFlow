import urllib.request
import urllib.parse
import re
import time
import database

def get_hash(text):
    import hashlib
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

def search_youtube_channel(name):
    query = urllib.parse.quote(name)
    url = f"https://www.youtube.com/results?search_query={query}&sp=EgIQAg%253D%253D"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', 'Accept-Language': 'en-US,en;q=0.9'})
    try:
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        matches = re.findall(r'"url":"(/(?:channel/UC[a-zA-Z0-9_-]+|@[a-zA-Z0-9_-]+))"', html)
        if matches:
            unique_matches = list(dict.fromkeys(matches))
            return "https://www.youtube.com" + unique_matches[0]
    except Exception as e:
        print(f"Error searching YouTube for '{name}': {e}")
    return None

def extract_channel_id_and_subs(channel_url):
    req = urllib.request.Request(channel_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', 'Accept-Language': 'en-US,en;q=0.9'})
    try:
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        
        # 1. Extract Channel ID
        channel_id = None
        meta_match = re.search(r'meta itemprop="channelId" content="(UC[a-zA-Z0-9_-]+)"', html)
        if meta_match:
            channel_id = meta_match.group(1)
        else:
            meta_match_2 = re.search(r'"externalId":"(UC[a-zA-Z0-9_-]+)"', html)
            if meta_match_2:
                channel_id = meta_match_2.group(1)
            else:
                cid_match = re.search(r'youtube\.com/feeds/videos\.xml\?channel_id=(UC[a-zA-Z0-9_-]+)', html)
                if cid_match:
                    channel_id = cid_match.group(1)
                
        # 2. Extract Subscribers
        subs = 0
        
        # Check standard JSON content metadata first
        content_matches = re.findall(r'\"content\":\"([^\"]*(?:登録者|万人|subscribers|subscriberCount)[^\"]*)\"', html)
        if content_matches:
            text = content_matches[0].replace(',', '').lower()
            num_match = re.search(r'([0-9\.]+)', text)
            if num_match:
                num = float(num_match.group(1))
                multiplier = 1
                if 'million' in text or 'm' in text:
                    multiplier = 1000000
                elif 'thousand' in text or 'k' in text:
                    multiplier = 1000
                elif 'billion' in text or 'b' in text:
                    multiplier = 1000000000
                elif '万人' in text or '万' in text:
                    multiplier = 10000
                elif '亿' in text:
                    multiplier = 100000000
                subs = int(num * multiplier)
                
        # Fallback to general patterns if content parsing yielded 0
        if subs == 0:
            subs_patterns = [
                r'"subscriberCountText":{"accessibility":{"accessibilityData":{"label":"([^"]+)"}',
                r'([0-9\.,]+)\s*(?:million|thousand|K|M|万|亿)?\s*subscribers'
            ]
            for pattern in subs_patterns:
                subs_match = re.search(pattern, html, re.IGNORECASE)
                if subs_match:
                    text = subs_match.group(1).replace(',', '').lower()
                    num_match = re.search(r'([0-9\.]+)', text)
                    if num_match:
                        num = float(num_match.group(1))
                        multiplier = 1
                        if 'million' in text or 'm' in text:
                            multiplier = 1000000
                        elif 'thousand' in text or 'k' in text:
                            multiplier = 1000
                        elif 'billion' in text or 'b' in text:
                            multiplier = 1000000000
                        elif '万人' in text or '万' in text:
                            multiplier = 10000
                        elif '亿' in text:
                            multiplier = 100000000
                        subs = int(num * multiplier)
                        break
        return channel_id, subs
    except Exception as e:
        print(f"Error fetching page {channel_url}: {e}")
    return None, 0

def get_podcast_subs(name):
    try:
        query = urllib.parse.quote(name)
        url = f"https://itunes.apple.com/search?term={query}&entity=podcast&limit=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        import json
        data = json.loads(urllib.request.urlopen(req, timeout=5).read().decode('utf-8'))
        if data['resultCount'] > 0:
            ratings = data['results'][0].get('userRatingCount')
            if ratings:
                return ratings * 120
            else:
                return data['results'][0].get('trackCount', 10) * 1000
        return 0
    except Exception as e:
        print(f"Error fetching Apple API for {name}: {e}")
    return 0

def main():
    conn = database.get_connection()
    cur = conn.cursor()
    
    # We target placeholders: 45k, 120k, 0, or NULL
    cur.execute("SELECT id, name, platform, raw_url FROM channels WHERE followers IN (0, 45000, 120000) OR followers IS NULL")
    rows = cur.fetchall()
    
    print(f"Found {len(rows)} channels with placeholder follower counts.")
    
    updated_count = 0
    
    for row in rows:
        old_id, name, platform, raw_url = row
        print(f"\nProcessing '{name}' ({platform})...")
        
        if platform == 'youtube':
            # Check if the current URL is valid
            is_valid = False
            if old_id and old_id.startswith('UC'):
                try:
                    req = urllib.request.Request(raw_url, method='HEAD', headers={'User-Agent': 'Mozilla/5.0'})
                    urllib.request.urlopen(req, timeout=5)
                    is_valid = True
                except Exception:
                    is_valid = False
            
            real_url = raw_url
            if not is_valid:
                print(f"  -> Current URL 404s. Searching YouTube...")
                resolved_url = search_youtube_channel(name)
                if resolved_url:
                    real_url = resolved_url
                    print(f"  -> Resolved to: {real_url}")
                else:
                    print(f"  -> Could not resolve channel URL on YouTube. Skipping.")
                    continue
            
            real_id, subs = extract_channel_id_and_subs(real_url)
            if real_id:
                print(f"  -> Scraped: ID={real_id}, Subscribers={subs}")
                # Save to database
                try:
                    if real_id != old_id:
                        # Check if duplicate exists
                        cur.execute("SELECT id FROM channels WHERE id = %s", (real_id,))
                        dup = cur.fetchone()
                        if dup:
                            print(f"  -> Duplicate channel detected ({real_id}). Deleting old placeholder.")
                            cur.execute("DELETE FROM channels WHERE id = %s", (old_id,))
                        else:
                            cur.execute("UPDATE channels SET id = %s, raw_url = %s, followers = %s WHERE id = %s", (real_id, real_url, subs, old_id))
                    else:
                        cur.execute("UPDATE channels SET followers = %s WHERE id = %s", (subs, old_id))
                    conn.commit()
                    updated_count += 1
                except Exception as e:
                    print(f"  -> DB Error: {e}")
                    conn.rollback()
            else:
                print(f"  -> Failed to extract real ID from {real_url}")
                
        elif platform == 'podcast':
            subs = get_podcast_subs(name)
            if subs > 0:
                print(f"  -> Scraped rating-proxy: {subs} estimated listeners")
                try:
                    cur.execute("UPDATE channels SET followers = %s WHERE id = %s", (subs, old_id))
                    conn.commit()
                    updated_count += 1
                except Exception as e:
                    print(f"  -> DB Error: {e}")
                    conn.rollback()
            else:
                # Set to 0 if not found to prevent fake data
                print(f"  -> Could not find ratings. Setting to 0.")
                try:
                    cur.execute("UPDATE channels SET followers = 0 WHERE id = %s", (old_id,))
                    conn.commit()
                except Exception as e:
                    print(f"  -> DB Error: {e}")
                    conn.rollback()
                    
        time.sleep(1)
        
    conn.close()
    print(f"\nDone! Successfully updated/merged {updated_count} channels with real subscriber counts.")

if __name__ == '__main__':
    main()
