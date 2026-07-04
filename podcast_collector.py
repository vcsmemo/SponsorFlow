import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import http.client
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from typing import List, Optional
from openai import OpenAI
import config
from parser import clean_and_extract_links, resolve_redirect, SponsorSignal, SponsorExtractionResult

# RSS/iTunes XML namespaces
NAMESPACES = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "content": "http://purl.org/rss/1.0/modules/content/"
}

class PodcastEpisode(BaseModel):
    title: str
    guid: str
    pub_date: str
    show_notes: str

def parse_rss_feed(feed_content: bytes) -> List[PodcastEpisode]:
    """
    Parses the RSS feed XML content and returns a list of PodcastEpisode objects.
    """
    root = ET.fromstring(feed_content)
    channel = root.find("channel")
    if channel is None:
        return []
        
    episodes = []
    for item in channel.findall("item"):
        title_el = item.find("title")
        guid_el = item.find("guid")
        pub_date_el = item.find("pubDate")
        
        # Try finding description or iTunes summary/content encoded
        desc_el = item.find("description")
        content_el = item.find("{http://purl.org/rss/1.0/modules/content/}encoded")
        itunes_summary_el = item.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}summary")
        
        title = title_el.text if title_el is not None else "Unknown Title"
        guid = guid_el.text if guid_el is not None else "Unknown GUID"
        pub_date = pub_date_el.text if pub_date_el is not None else ""
        
        # Combine possible sources of show notes
        notes_html = ""
        if content_el is not None and content_el.text:
            notes_html = content_el.text
        elif desc_el is not None and desc_el.text:
            notes_html = desc_el.text
        elif itunes_summary_el is not None and itunes_summary_el.text:
            notes_html = itunes_summary_el.text
            
        cleaned_notes = clean_and_extract_links(notes_html) if notes_html else ""
        
        episodes.append(PodcastEpisode(
            title=title,
            guid=guid,
            pub_date=pub_date,
            show_notes=cleaned_notes
        ))
        
    return episodes

def extract_sponsors_from_episode(show_title: str, episode: PodcastEpisode) -> List[SponsorSignal]:
    """
    Queries Kimi to extract structured sponsor signals from the episode show notes.
    """
    client = OpenAI(api_key=config.KIMI_API_KEY, base_url=config.KIMI_BASE_URL)
    
    prompt = (
        f"Podcast Show: {show_title}\n"
        f"Episode Title: {episode.title}\n"
        f"Published Date: {episode.pub_date}\n\n"
        f"Show Notes Content:\n{episode.show_notes}"
    )
    
    schema_instructions = """
You are an expert sponsorship extraction bot. Analyze the podcast episode show notes and extract all sponsors, promotional links, descriptions/summaries of ad copies, and any promo codes.
You must output a JSON object containing a "sponsors" array where each sponsor has:
- sponsor_name (string)
- sponsor_url (string)
- newsletter_source (string, show name)
- ad_copy_summary (string)
- detected_promo_codes (array of strings)

Example:
{
  "sponsors": [
    {
      "sponsor_name": "Example Corp",
      "sponsor_url": "https://example.com/promo",
      "newsletter_source": "The Founders Brainstorm",
      "ad_copy_summary": "Sponsor description",
      "detected_promo_codes": ["PROMO1"]
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
        
        import json
        raw_content = response.choices[0].message.content
        data = json.loads(raw_content)
        
        sponsors = []
        for item in data.get("sponsors", []):
            sponsors.append(SponsorSignal(
                sponsor_name=item.get("sponsor_name") or "Unknown",
                sponsor_url=item.get("sponsor_url") or "",
                newsletter_source=show_title,
                ad_copy_summary=item.get("ad_copy_summary") or "",
                detected_promo_codes=item.get("detected_promo_codes") or []
            ))
    except Exception as e:
        print(f"Kimi LLM extraction error for podcast: {e}")
        return []
        
    # Clean/Resolve sponsor redirect URLs
    for sponsor in sponsors:
        if sponsor.sponsor_url:
            sponsor.sponsor_url = resolve_redirect(sponsor.sponsor_url)
            
    return sponsors

def process_feed(feed_url: str) -> List[SponsorSignal]:
    """
    Fetches a podcast RSS feed and processes the episodes to extract sponsors.
    """
    config.validate_config("llm")
    print(f"Fetching RSS feed: {feed_url}")
    
    headers = {"User-Agent": "SponsorFlowAggregator/1.0"}
    req = urllib.request.Request(feed_url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as response:
        feed_content = response.read()
        
    root = ET.fromstring(feed_content)
    channel = root.find("channel")
    show_title = channel.find("title").text if channel is not None and channel.find("title") is not None else "Podcast"
    
    episodes = parse_rss_feed(feed_content)
    print(f"Parsed {len(episodes)} episodes from '{show_title}'.")
    
    all_sponsors = []
    # Process the 3 most recent episodes as a test/sample rate limiting
    for ep in episodes[:3]:
        print(f"Analyzing episode: {ep.title}")
        sponsors = extract_sponsors_from_episode(show_title, ep)
        print(f"Found {len(sponsors)} sponsor(s).")
        all_sponsors.extend(sponsors)
        
    return all_sponsors

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test-file":
        if len(sys.argv) < 3:
            print("Please provide a path to a test XML RSS file.")
            sys.exit(1)
        test_file_path = sys.argv[2]
        print(f"Running in local dry-run mode using feed file: {test_file_path}")
        
        with open(test_file_path, "rb") as f:
            feed_content = f.read()
            
        root = ET.fromstring(feed_content)
        channel = root.find("channel")
        show_title = channel.find("title").text if channel is not None and channel.find("title") is not None else "Test Podcast"
        
        episodes = parse_rss_feed(feed_content)
        print(f"Parsed {len(episodes)} episodes.")
        
        for ep in episodes[:2]:
            print(f"\n--- Episode: {ep.title} ---")
            if config.KIMI_API_KEY:
                sponsors = extract_sponsors_from_episode(show_title, ep)
                for idx, sp in enumerate(sponsors, 1):
                    print(f"  [Sponsor #{idx}]")
                    print(f"  Name: {sp.sponsor_name}")
                    print(f"  URL: {sp.sponsor_url}")
                    print(f"  Promo Codes: {sp.detected_promo_codes}")
                    print(f"  Summary: {sp.ad_copy_summary}")
            else:
                print("Cleaned show notes preview (first 400 chars):")
                print(ep.show_notes[:400])
    else:
        # Default test RSS feed URL (e.g. Lenny's Podcast on Spotify or generic public feeds)
        # We can run it if a URL is provided
        if len(sys.argv) > 1:
            feed_url = sys.argv[1]
            try:
                sponsors = process_feed(feed_url)
                for sp in sponsors:
                    print(sp.model_dump_json(indent=2))
            except Exception as e:
                print(f"Failed to process feed: {e}")
        else:
            print("Usage: python podcast_collector.py <feed_url> OR python podcast_collector.py --test-file <xml_file>")
