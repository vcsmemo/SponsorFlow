import imaplib
import email
from email.header import decode_header
import re
import urllib.parse
import http.client
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from typing import List, Optional
from openai import OpenAI
import config

# Define Pydantic schemas for Structured Outputs
class SponsorSignal(BaseModel):
    sponsor_name: str = Field(description="The name of the sponsoring brand/company.")
    sponsor_url: str = Field(description="The sponsor's destination URL (e.g. promo landing page or primary website). If multiple links exist, prioritize the promo/destination link.")
    newsletter_source: str = Field(description="The sender or title of the newsletter source.")
    ad_copy_summary: str = Field(description="A brief summary of the sponsor's ad copy or pitch from the email.")
    detected_promo_codes: List[str] = Field(default=[], description="List of detected promo codes or discount codes associated with this sponsor.")

class SponsorExtractionResult(BaseModel):
    sponsors: List[SponsorSignal] = Field(description="List of all sponsors identified in the newsletter.")

def clean_and_extract_links(html_content: str):
    """
    Parses HTML content, extracts and maps links, 
    and returns a cleaned text representation that includes inline link mappings
    to help the LLM identify sponsor URLs.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Extract links map and rewrite anchors to format: Text [URL: http...]
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(strip=True)
        if href.startswith(("http://", "https://")) and text:
            # Avoid repeating if the link text is just the URL itself
            if text.startswith(("http://", "https://")) or len(text) < 2:
                a.replace_with(f" [Link: {href}] ")
            else:
                a.replace_with(f" {text} [Link: {href}] ")
                
    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
        
    text = soup.get_text(separator="\n")
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    cleaned_text = "\n".join(chunk for chunk in chunks if chunk)
    return cleaned_text

def resolve_redirect(url: str, max_depth: int = 3) -> str:
    """
    Follows HTTP redirects to extract the actual destination URL if possible.
    """
    if max_depth <= 0:
        return url
        
    try:
        parsed = urllib.parse.urlparse(url)
        # Use http.client for lightweight check without extra heavy dependencies
        conn_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        conn = conn_cls(parsed.netloc, timeout=3)
        path = parsed.path + ("?" + parsed.query if parsed.query else "")
        conn.request("HEAD", path or "/", headers={"User-Agent": "SponsorFlowAggregator/1.0"})
        res = conn.getresponse()
        
        if res.status in (301, 302, 303, 307, 308):
            loc = res.getheader("Location")
            if loc:
                next_url = urllib.parse.urljoin(url, loc)
                return resolve_redirect(next_url, max_depth - 1)
    except Exception:
        # If redirect resolution fails (e.g. timeout or SSL error), return original
        pass
    return url

def decode_mime_header(header_value: Optional[str]) -> str:
    if not header_value:
        return ""
    decoded = decode_header(header_value)
    parts = []
    for text, encoding in decoded:
        if isinstance(text, bytes):
            parts.append(text.decode(encoding or "utf-8", errors="replace"))
        else:
            parts.append(text)
    return "".join(parts)

def fetch_unread_emails():
    """
    Connects to the IMAP server and retrieves unread emails.
    Yields dicts with headers and body content.
    """
    config.validate_config()
    
    # Establish connection
    mail = imaplib.IMAP4_SSL(config.IMAP_SERVER, config.IMAP_PORT)
    mail.login(config.IMAP_EMAIL, config.IMAP_PASSWORD)
    mail.select("inbox")
    
    # Search for unread emails
    status, messages = mail.search(None, "UNSEEN")
    if status != "OK" or not messages[0]:
        print("No new emails found.")
        mail.close()
        mail.logout()
        return

    mail_ids = messages[0].split()
    print(f"Found {len(mail_ids)} unread email(s). Processing...")

    for mail_id in mail_ids:
        try:
            status, data = mail.fetch(mail_id, "(RFC822)")
            if status != "OK":
                continue
            
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            subject = decode_mime_header(msg.get("Subject"))
            sender = decode_mime_header(msg.get("From"))
            
            # Extract email body
            body_html = ""
            body_text = ""
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    if "attachment" in content_disposition:
                        continue
                        
                    try:
                        payload = part.get_payload(decode=True)
                        if not payload:
                            continue
                        charset = part.get_content_charset() or "utf-8"
                        text = payload.decode(charset, errors="replace")
                        
                        if content_type == "text/html":
                            body_html = text
                        elif content_type == "text/plain":
                            body_text = text
                    except Exception as e:
                        print(f"Error decoding email part: {e}")
            else:
                try:
                    payload = msg.get_payload(decode=True)
                    charset = msg.get_content_charset() or "utf-8"
                    body_text = payload.decode(charset, errors="replace")
                except Exception as e:
                    print(f"Error decoding single-part email: {e}")
            
            # Prefer HTML for parsing since we can extract clean link structures
            if body_html:
                cleaned_body = clean_and_extract_links(body_html)
            else:
                cleaned_body = body_text
                
            yield {
                "id": mail_id,
                "sender": sender,
                "subject": subject,
                "body": cleaned_body
            }
            
        except Exception as e:
            print(f"Error processing email ID {mail_id.decode()}: {e}")
            
    mail.close()
    mail.logout()

def extract_sponsors_from_email(email_data: dict) -> List[SponsorSignal]:
    """
    Sends email content to Kimi API to parse sponsors.
    """
    client = OpenAI(api_key=config.KIMI_API_KEY, base_url=config.KIMI_BASE_URL, timeout=30.0)
    
    prompt = f"From: {email_data['sender']}\nSubject: {email_data['subject']}\n\nEmail Content:\n{email_data['body']}"
    
    schema_instructions = """
You are an expert sponsorship extraction bot. Analyze the given newsletter text and extract all sponsors, promotional links, descriptions/summaries of ad copies, and any promo codes.
You must output a JSON object containing a "sponsors" array where each sponsor has:
- sponsor_name (string)
- sponsor_url (string)
- newsletter_source (string, sender name)
- ad_copy_summary (string)
- detected_promo_codes (array of strings)

Example:
{
  "sponsors": [
    {
      "sponsor_name": "Acme Corp",
      "sponsor_url": "https://acme.xyz",
      "newsletter_source": "Daily Digest",
      "ad_copy_summary": "SaaS dashboard tools",
      "detected_promo_codes": ["TECHFLOW20"]
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
                newsletter_source=item.get("newsletter_source") or email_data['sender'],
                ad_copy_summary=item.get("ad_copy_summary") or "",
                detected_promo_codes=item.get("detected_promo_codes") or []
            ))
    except Exception as e:
        print(f"Kimi LLM extraction error: {e}")
        return []
    
    # Try resolving redirect links to make the URLs clean
    for sponsor in sponsors:
        if sponsor.sponsor_url:
            sponsor.sponsor_url = resolve_redirect(sponsor.sponsor_url)
            
    return sponsors

if __name__ == "__main__":
    import sys
    # Add dry-run or debug command line argument handling
    if len(sys.argv) > 1 and sys.argv[1] == "--test-file":
        if len(sys.argv) < 3:
            print("Please provide a path to a test HTML/text file.")
            sys.exit(1)
        test_file_path = sys.argv[2]
        print(f"Running in local dry-run mode using file: {test_file_path}")
        with open(test_file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if test_file_path.endswith(".html"):
            cleaned = clean_and_extract_links(content)
        else:
            cleaned = content
            
        test_email = {
            "sender": "TLDR Newsletter <tldr@tldrnewsletter.com>",
            "subject": "TLDR 2026-06-20",
            "body": cleaned
        }
        
        # Test LLM parsing if key is available
        if config.KIMI_API_KEY:
            print("Extracting sponsors using Kimi API...")
            sponsors = extract_sponsors_from_email(test_email)
            for idx, sp in enumerate(sponsors, 1):
                print(f"\n[Sponsor #{idx}]")
                print(f"Name: {sp.sponsor_name}")
                print(f"URL: {sp.sponsor_url}")
                print(f"Source: {sp.newsletter_source}")
                print(f"Promo Codes: {sp.detected_promo_codes}")
                print(f"Summary: {sp.ad_copy_summary}")
        else:
            print("Cleaned text preview (first 500 chars):")
            print(cleaned[:500])
            print("\n(Set MOONSHOT_API_KEY / OPENAI_API_KEY in environment to run the LLM extraction step.)")
    else:
        # Standard email retrieval execution flow
        try:
            for email_item in fetch_unread_emails():
                print(f"\nProcessing Email: '{email_item['subject']}' from {email_item['sender']}")
                sponsors = extract_sponsors_from_email(email_item)
                print(f"Found {len(sponsors)} sponsor(s).")
                for sp in sponsors:
                    print(sp.model_dump_json(indent=2))
        except Exception as e:
            print(f"Execution failed: {e}")
