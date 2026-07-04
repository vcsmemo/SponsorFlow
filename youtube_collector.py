import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Optional
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
import config
from parser import SponsorSignal, resolve_redirect

class YouTubeVideo(BaseModel):
    video_id: str
    title: str
    channel_title: str
    published_at: Optional[str] = None

def fetch_channel_videos(channel_id: str) -> List[YouTubeVideo]:
    """
    Fetches the 15 most recent videos for a given YouTube channel ID using public XML feeds.
    """
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    print(f"Fetching YouTube public feed: {feed_url}")
    headers = {"User-Agent": "SponsorFlowAggregator/1.0"}
    
    try:
        req = urllib.request.Request(feed_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        # Handle Atom namespace
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        
        channel_title = "YouTube Channel"
        author_el = root.find("atom:author", ns)
        if author_el is not None:
            name_el = author_el.find("atom:name", ns)
            if name_el is not None:
                channel_title = name_el.text
                
        videos = []
        for entry in root.findall("atom:entry", ns):
            video_id_el = entry.find("atom:id", ns)
            title_el = entry.find("atom:title", ns)
            published_el = entry.find("atom:published", ns)
            
            if video_id_el is not None and title_el is not None:
                # atom:id is in format yt:video:VIDEO_ID
                parts = video_id_el.text.split(":")
                video_id = parts[-1] if len(parts) > 0 else video_id_el.text
                videos.append(YouTubeVideo(
                    video_id=video_id,
                    title=title_el.text,
                    channel_title=channel_title,
                    published_at=published_el.text if published_el is not None else None
                ))
        return videos
    except Exception as e:
        print(f"Error fetching channel feed for {channel_id}: {e}")
        return []

def get_sponsor_segments(video_id: str) -> List[dict]:
    """
    Queries SponsorBlock API for sponsor skip segments.
    """
    url = f"https://sponsor.ajay.app/api/skipSegments?videoID={video_id}&category=sponsor"
    headers = {"User-Agent": "SponsorFlowAggregator/1.0"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                return data
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # 404 simply means no sponsor segments exist for this video
            return []
        print(f"SponsorBlock HTTP Error {e.code} for video {video_id}")
    except Exception as e:
        print(f"SponsorBlock connection error for video {video_id}: {e}")
    return []

def fetch_segment_transcript(video_id: str, start: float, end: float) -> str:
    """
    Downloads captions and extracts text falling within the start and end timestamps (with a buffer).
    """
    # 5 seconds buffer on either side
    buffer = 5.0
    start_buffered = max(0, start - buffer)
    end_buffered = end + buffer
    
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US'])
        segment_lines = []
        for item in transcript_list:
            item_start = item['start']
            # If the caption line falls within the window
            if item_start >= start_buffered and item_start <= end_buffered:
                segment_lines.append(item['text'])
                
        return " ".join(segment_lines)
    except Exception as e:
        print(f"Failed to fetch captions/transcript for {video_id}: {e}")
        return ""

def extract_sponsor_from_transcript(video: YouTubeVideo, transcript_snippet: str) -> Optional[SponsorSignal]:
    """
    Queries Kimi LLM to parse sponsor information from transcript segment text.
    """
    if not transcript_snippet:
        return None
        
    client = OpenAI(api_key=config.KIMI_API_KEY, base_url=config.KIMI_BASE_URL)
    
    prompt = (
        f"YouTube Channel: {video.channel_title}\n"
        f"Video Title: {video.title}\n"
        f"Video ID: {video.video_id}\n\n"
        f"Sponsor Segment Captions:\n{transcript_snippet}"
    )
    
    schema_instructions = """
You are an expert sponsorship extraction bot. Analyze the auto-generated captions of a YouTube sponsor segment.
Extract the sponsoring brand details.
IMPORTANT RULES:
1. ONLY extract true commercial third-party sponsorships (brands paying for ad placements).
2. DO NOT extract self-promotions (e.g., the YouTuber's own merch, course, or patreon).
3. DO NOT extract standard gear affiliate links or portfolio companies for corporate channels.

You must output a JSON object containing a "sponsors" array with at most 1 item representing the sponsor:
- sponsor_name (string, company/brand name)
- sponsor_url (string, promo landing page mentioned, or the main website URL. Use YouTube video descriptions / general site patterns if URL not fully spelled out in text. If not found, guess based on brand name or output blank string)
- newsletter_source (string, YouTube channel title)
- ad_copy_summary (string, brief summary of their pitch in this video)
- detected_promo_codes (array of strings, discount codes mentioned in text)

Example:
{
  "sponsors": [
    {
      "sponsor_name": "NordVPN",
      "sponsor_url": "https://nordvpn.com/promo",
      "newsletter_source": "Linus Tech Tips",
      "ad_copy_summary": "Encrypt your online traffic with NordVPN to secure your personal data",
      "detected_promo_codes": ["LINUS"]
    }
  ]
}
"""
    try:
        response = client.chat.completions.create(
            model=config.KIMI_MODEL,
            messages=[
                {"role": "system", "content": schema_instructions},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        data = json.loads(response.choices[0].message.content)
        sponsors = data.get("sponsors", [])
        if sponsors:
            item = sponsors[0]
            # Map values into SponsorSignal
            sponsor = SponsorSignal(
                sponsor_name=item.get("sponsor_name") or "Unknown",
                sponsor_url=item.get("sponsor_url") or "",
                newsletter_source=video.channel_title,
                ad_copy_summary=item.get("ad_copy_summary") or "",
                detected_promo_codes=item.get("detected_promo_codes") or [],
                detected_at=video.published_at
            )
            
            # Resolve url redirect
            if sponsor.sponsor_url:
                sponsor.sponsor_url = resolve_redirect(sponsor.sponsor_url)
            return sponsor
    except Exception as e:
        print(f"Kimi LLM extraction error for YouTube video {video.video_id}: {e}")
    return None

def process_youtube_channel(channel_id: str) -> List[SponsorSignal]:
    """
    Process recent videos from a channel, checks SponsorBlock, downloads transcript segments,
    and extracts structured sponsor info.
    """
    config.validate_config("llm")
    videos = fetch_channel_videos(channel_id)
    print(f"Found {len(videos)} recent videos.")
    
    extracted_sponsors = []
    # Check the first 5 videos to be rate-limit friendly
    for video in videos[:5]:
        print(f"Checking video: {video.title} (ID: {video.video_id})")
        segments = get_sponsor_segments(video.video_id)
        if segments:
            print(f"  Found {len(segments)} sponsor segment(s) on SponsorBlock.")
            for segment_data in segments:
                segment = segment_data.get("segment", [0, 0])
                start, end = segment[0], segment[1]
                print(f"  Fetching caption segment: {start}s to {end}s")
                transcript = fetch_segment_transcript(video.video_id, start, end)
                if transcript:
                    sponsor = extract_sponsor_from_transcript(video, transcript)
                    if sponsor:
                        print(f"  Extracted Sponsor: {sponsor.sponsor_name}")
                        extracted_sponsors.append(sponsor)
        else:
            print("  No sponsor segments found.")
            
    return extracted_sponsors

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test-video":
        if len(sys.argv) < 3:
            print("Please provide a YouTube video ID.")
            sys.exit(1)
        video_id = sys.argv[2]
        print(f"Running dry-run verification for video ID: {video_id}")
        
        segments = get_sponsor_segments(video_id)
        print(f"SponsorBlock segments found: {segments}")
        if segments:
            for seg in segments:
                seg_range = seg.get("segment", [0, 0])
                print(f"Fetching segment: {seg_range[0]}s - {seg_range[1]}s")
                transcript = fetch_segment_transcript(video_id, seg_range[0], seg_range[1])
                print("Transcript Snippet:")
                print(transcript[:500])
                
                # Test LLM parsing if Kimi is configured
                if config.KIMI_API_KEY:
                    mock_video = YouTubeVideo(
                        video_id=video_id,
                        title="Dry Run Video Title",
                        channel_title="Dry Run Channel"
                    )
                    sponsor = extract_sponsor_from_transcript(mock_video, transcript)
                    if sponsor:
                        print("\nExtracted Sponsor Data:")
                        print(sponsor.model_dump_json(indent=2))
        else:
            print("No segments found for this video. Try video ID: 'p-1F76vR22E' or another recently sponsored video.")
    else:
        # Standard channel execution demo
        if len(sys.argv) > 1:
            channel_id = sys.argv[1]
            try:
                sponsors = process_youtube_channel(channel_id)
                for sp in sponsors:
                    print(sp.model_dump_json(indent=2))
            except Exception as e:
                print(f"Failed to process channel: {e}")
        else:
            print("Usage: python youtube_collector.py <channel_id> OR python youtube_collector.py --test-video <video_id>")
