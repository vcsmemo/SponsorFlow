#!/usr/bin/env python3
"""
extract_deals_from_yt.py — SponsorFlow Real Deals Extractor
============================================================
Fetches recent YouTube videos via RSS, parses descriptions for sponsor mentions,
writes verified deals into the sponsorship_signals table.

Usage:
    python3 extract_deals_from_yt.py [--limit N] [--dry-run]
"""
import re
import time
import hashlib
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.request import urlopen, Request
import database

SPONSOR_TRIGGERS = [
    r"(?:this (?:video|episode) is )?(?:sponsored|brought to you) by\s+([A-Za-z][A-Za-z0-9\s\.\-]{1,40}?)(?:\.|,|!|\n|$|\s{2}|\s(?:today|for))",
    r"(?:big )?thanks? to\s+([A-Za-z][A-Za-z0-9\s\.\-]{1,40}?)\s+for (?:sponsoring|supporting)",
    r"(?:today(?:'s)? sponsor is|our sponsor today is)\s+([A-Za-z][A-Za-z0-9\s\.\-]{1,40}?)(?:\.|,|!|\n|$)",
    r"(?:use (?:my|our) (?:link|code|promo)|promo code|coupon code)\s+[\w\-]+\s+(?:at|for|on)\s+([A-Za-z][A-Za-z0-9\s\.\-]{1,40}?)(?:\.|,|!|\n|$)",
    r"(?:special offer|free trial) (?:from|at|with)\s+([A-Za-z][A-Za-z0-9\s\.\-]{1,40}?)(?:\.|,|!|\n|$)",
]

SKIP_BRANDS = {
    "my","the","a","an","us","you","me","this","that","it","youtube","google",
    "twitter","instagram","tiktok","linkedin","today","now","new","more","free",
    "link","video","here","them","their","our","your","his","her","we","they",
}

BRAND_ALIASES = {
    "cursor ai":"Cursor","cursor":"Cursor","notion":"Notion","linear":"Linear",
    "raycast":"Raycast","nordvpn":"NordVPN","nord vpn":"NordVPN",
    "expressvpn":"ExpressVPN","surfshark":"Surfshark","squarespace":"Squarespace",
    "shopify":"Shopify","skillshare":"Skillshare","brilliant":"Brilliant",
    "audible":"Audible","aws":"AWS","hubspot":"HubSpot","salesforce":"Salesforce",
    "monday":"Monday.com","monday com":"Monday.com","clickup":"ClickUp",
    "asana":"Asana","figma":"Figma","retool":"Retool","datadog":"Datadog",
    "openai":"OpenAI","anthropic":"Anthropic","claude":"Anthropic",
    "perplexity":"Perplexity AI","perplexity ai":"Perplexity AI",
    "grammarly":"Grammarly","zapier":"Zapier","airtable":"Airtable",
    "supabase":"Supabase","cloudflare":"Cloudflare","warp":"Warp Terminal",
    "1password":"1Password","lastpass":"LastPass","bitwarden":"Bitwarden",
    "robinhood":"Robinhood","coinbase":"Coinbase","binance":"Binance",
    "hostinger":"Hostinger","bluehost":"Bluehost","loom":"Loom",
    "codeium":"Codeium","trading 212":"Trading 212","vercel":"Vercel",
    "netlify":"Netlify","render":"Render","railway":"Railway",
}

NS = {
    "atom":"http://www.w3.org/2005/Atom",
    "yt":"http://www.youtube.com/xml/schemas/2015",
    "media":"http://search.yahoo.com/mrss/",
}

def fetch_channel_videos(channel_id, max_videos=15):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            content = resp.read()
        root = ET.fromstring(content)
        videos = []
        for entry in root.findall("atom:entry", NS)[:max_videos]:
            vid = entry.find("yt:videoId", NS)
            ttl = entry.find("atom:title", NS)
            pub = entry.find("atom:published", NS)
            dsc = entry.find("media:group/media:description", NS)
            if not vid:
                continue
            videos.append({
                "video_id": vid.text or "",
                "title": (ttl.text or "") if ttl is not None else "",
                "published": (pub.text or "") if pub is not None else "",
                "description": (dsc.text or "") if dsc is not None else "",
            })
        return videos
    except Exception:
        return []

def extract_sponsors(text):
    if not text or len(text) < 20:
        return []
    tl = text.lower()
    kws = ["sponsor","brought to you","thanks to","promo code","coupon","use code","use my link","affiliate","partner"]
    if not any(k in tl for k in kws):
        return []
    found = []
    seen = set()
    for pat in SPONSOR_TRIGGERS:
        for m in re.finditer(pat, text, re.IGNORECASE | re.MULTILINE):
            raw = m.group(1).strip().rstrip(".,!;:\"'")
            if not raw or len(raw) < 2 or len(raw) > 50:
                continue
            rl = raw.lower().strip()
            if rl in SKIP_BRANDS or rl.isdigit():
                continue
            canon = BRAND_ALIASES.get(rl, raw.title())
            if canon.lower() in seen:
                continue
            seen.add(canon.lower())
            found.append({"brand":canon,"product":canon,"cta":""})
    return found[:3]

def get_or_create_sponsor(conn, brand_name):
    rows = database.execute_query(conn, "SELECT id FROM sponsors WHERE LOWER(brand_name) = LOWER(?)", (brand_name,))
    if rows:
        return rows[0]["id"]
    sid = f"sp_{hashlib.md5(brand_name.lower().encode()).hexdigest()[:12]}"
    bl = brand_name.lower()
    if any(k in bl for k in ["vpn","nord","surf","express"]):
        ind = "Security / Privacy"
    elif any(k in bl for k in ["ai","gpt","cursor","openai","claude","codeium","tabnine"]):
        ind = "AI / Developer Tools"
    elif any(k in bl for k in ["trade","invest","coin","finance","stock","robinhood","binance"]):
        ind = "Finance / Investing"
    elif any(k in bl for k in ["learn","skill","course","brilliant","udemy"]):
        ind = "Education"
    elif any(k in bl for k in ["host","cloud","server","deploy","netlify","vercel","railway"]):
        ind = "Cloud / Hosting"
    else:
        ind = "SaaS / Tech"
    try:
        database.execute_write(conn, "INSERT INTO sponsors (id, brand_name, industry_tag) VALUES (?,?,?)", (sid, brand_name, ind))
        return sid
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            rows = database.execute_query(conn, "SELECT id FROM sponsors WHERE LOWER(brand_name) = LOWER(?)", (brand_name,))
            return rows[0]["id"] if rows else None
        return None

def write_signal(conn, channel_id, sponsor_id, video, sp_info):
    key = f"{channel_id}_{sponsor_id}_{video['video_id']}"
    sig_id = f"sig_{hashlib.md5(key.encode()).hexdigest()[:16]}"
    rows = database.execute_query(conn, "SELECT id FROM sponsorship_signals WHERE id = ?", (sig_id,))
    if rows:
        return False
    try:
        dt = datetime.fromisoformat(video["published"].replace("Z","+00:00"))
        det = dt.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        det = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    src = f"https://www.youtube.com/watch?v={video['video_id']}"
    ad = video["description"][:1000] if video["description"] else ""
    try:
        database.execute_write(conn,
            "INSERT INTO sponsorship_signals (id,channel_id,sponsor_id,detected_at,ad_copy,source_url,product,cta,sponsor_type,confidence) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (sig_id, channel_id, sponsor_id, det, ad, src, sp_info.get("product","")[:100], sp_info.get("cta","")[:200], "YouTube Sponsorship", 0.75)
        )
        return True
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return False
        print(f"  ⚠️  Error: {e}")
        return False

def run(limit=None, dry_run=False, delay=0.5):
    print("="*60)
    print("SponsorFlow — YouTube Deals Extractor")
    print("="*60)
    conn = database.get_connection()
    channels = database.execute_query(conn,
        "SELECT id, name, followers FROM channels WHERE platform = 'youtube' ORDER BY followers DESC"
    )
    if not channels:
        print("❌ No YouTube channels found.")
        return
    if limit:
        channels = channels[:limit]
    print(f"📺 Processing {len(channels)} YouTube channels...")
    total_videos = 0
    total_written = 0
    for i, ch in enumerate(channels):
        cid = ch["id"]
        cname = ch["name"]
        videos = fetch_channel_videos(cid)
        if not videos:
            time.sleep(delay)
            continue
        total_videos += len(videos)
        ch_new = 0
        for video in videos:
            txt = f"{video['title']}\n{video['description']}"
            sponsors = extract_sponsors(txt)
            for sp in sponsors:
                if dry_run:
                    print(f"  [DRY RUN] {cname}: {sp['brand']} — '{video['title'][:50]}'")
                    continue
                sid = get_or_create_sponsor(conn, sp["brand"])
                if sid and write_signal(conn, cid, sid, video, sp):
                    total_written += 1
                    ch_new += 1
        if ch_new > 0:
            print(f"  [{i+1}/{len(channels)}] {cname}: +{ch_new} deals")
        time.sleep(delay)
        if (i+1) % 50 == 0:
            print(f"\n📊 Progress: {i+1}/{len(channels)} channels | {total_written} deals written\n")
    conn.close()
    print()
    print("="*60)
    print(f"✅ Done! Videos scanned: {total_videos} | New deals: {total_written}")
    print("="*60)

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Extract deals from YouTube RSS")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--delay", type=float, default=0.5)
    args = p.parse_args()
    run(limit=args.limit, dry_run=args.dry_run, delay=args.delay)
