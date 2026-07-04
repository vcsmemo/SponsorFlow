import json
import config
from openai import OpenAI

config.validate_config("llm")
client = OpenAI(api_key=config.KIMI_API_KEY, base_url=config.KIMI_BASE_URL)

prompt = """
Generate a JSON object with two arrays: 'youtube' and 'podcasts'.
We need 5 popular YouTube channels in Tech, Finance, AI, or Business (include their exact YouTube channel_id starting with UC).
We need 5 popular Podcasts in Tech, Finance, AI, or Business (include their exact RSS URL).
Format:
{
  "youtube": [{"name": "Channel Name", "channel_id": "UC...", "category": "Tech"}],
  "podcasts": [{"name": "Podcast Name", "rss_url": "https://...", "category": "Tech"}]
}
Please provide REAL channel IDs and REAL RSS URLs if possible.
"""

try:
    response = client.chat.completions.create(
        model=config.KIMI_MODEL,
        messages=[{"role": "system", "content": "You are a data extraction assistant. Output ONLY valid JSON."},
                  {"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    data = json.loads(response.choices[0].message.content)

    with open('data/feeds_youtube.json', 'r') as f:
        yt = json.load(f)
    yt.extend(data.get('youtube', []))
    with open('data/feeds_youtube.json', 'w') as f:
        json.dump(yt, f, indent=2)

    with open('data/feeds_podcasts.json', 'r') as f:
        pod = json.load(f)
    pod.extend(data.get('podcasts', []))
    with open('data/feeds_podcasts.json', 'w') as f:
        json.dump(pod, f, indent=2)

    print(f"Added {len(data.get('youtube', []))} YouTube channels and {len(data.get('podcasts', []))} Podcasts.")
except Exception as e:
    print(f"Failed: {e}")
