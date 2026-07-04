import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Kimi (Moonshot AI) API configurations
KIMI_API_KEY = os.getenv("MOONSHOT_API_KEY") or os.getenv("OPENAI_API_KEY")
KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshot-v1-8k")

# IMAP configurations
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
IMAP_EMAIL = os.getenv("IMAP_EMAIL")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")

def validate_config(scope="all"):
    missing = []
    if scope in ("all", "llm"):
        if not KIMI_API_KEY:
            missing.append("MOONSHOT_API_KEY / OPENAI_API_KEY")
    if scope in ("all", "email"):
        if not IMAP_EMAIL:
            missing.append("IMAP_EMAIL")
        if not IMAP_PASSWORD:
            missing.append("IMAP_PASSWORD")
    
    if missing:
        raise ValueError(f"Missing required environment configuration for '{scope}': {', '.join(missing)}")
