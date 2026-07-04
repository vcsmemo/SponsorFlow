import sqlite3
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Load environment variables (supports fallback)
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
DB_FILE = "sponsorflow.db"

def clean_db_url(url_str):
    if not url_str:
        return url_str
    try:
        parsed = urlparse(url_str)
        if parsed.scheme not in ('postgres', 'postgresql'):
            return url_str
        
        # Only keep query parameters supported by libpq
        supported = {
            'sslmode', 'sslkey', 'sslcert', 'sslrootcert', 'sslcrl',
            'sslcompression', 'service', 'target_session_attrs',
            'connect_timeout', 'options', 'application_name', 'keepalives',
            'keepalives_idle', 'keepalives_interval', 'keepalives_count',
            'tcp_user_timeout', 'gssencmode', 'channel_binding'
        }
        
        qsl = parse_qsl(parsed.query)
        filtered = [(k, v) for k, v in qsl if k.lower() in supported]
        
        new_query = urlencode(filtered)
        cleaned = urlunparse(parsed._replace(query=new_query))
        return cleaned
    except Exception:
        return url_str

CLEANED_SUPABASE_DB_URL = clean_db_url(SUPABASE_DB_URL)

# Try importing psycopg2 for Supabase PostgreSQL support
HAS_POSTGRES = False
if CLEANED_SUPABASE_DB_URL:
    try:
        import psycopg2
        import psycopg2.extras
        HAS_POSTGRES = True
        print("Supabase/PostgreSQL connection URL detected. Database engine set to PostgreSQL.")
    except ImportError:
        print("SUPABASE_DB_URL detected but psycopg2 is not installed. Falling back to local SQLite.")

def get_connection():
    global HAS_POSTGRES
    if HAS_POSTGRES and CLEANED_SUPABASE_DB_URL:
        try:
            conn = psycopg2.connect(CLEANED_SUPABASE_DB_URL)
            return conn
        except Exception as e:
            print(f"Failed to connect to Supabase/PostgreSQL: {e}")
            print("Falling back to local SQLite.")
            HAS_POSTGRES = False  # Set to False so subsequent calls default to SQLite
            
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(conn, sql: str, params=()):
    """
    Executes a single SQL query, translating '?' placeholders to '%s' if on PostgreSQL.
    Returns row dictionary lists.
    """
    cursor = conn.cursor()
    if HAS_POSTGRES:
        sql = sql.replace("?", "%s")
        cursor.execute(sql, params)
        if cursor.description:
            columns = [col[0] for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        else:
            rows = []
    else:
        cursor.execute(sql, params)
        rows = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    return rows

def execute_write(conn, sql: str, params=()):
    """
    Executes a single write query (INSERT/UPDATE/DELETE), translating placeholders.
    """
    cursor = conn.cursor()
    if HAS_POSTGRES:
        sql = sql.replace("?", "%s")
    cursor.execute(sql, params)
    conn.commit()
    cursor.close()

def execute_many(conn, sql: str, params_list):
    """
    Executes a batch write query.
    """
    cursor = conn.cursor()
    if HAS_POSTGRES:
        sql = sql.replace("?", "%s")
    cursor.executemany(sql, params_list)
    conn.commit()
    cursor.close()

def init_db():
    """
    Initializes the database. Executes dialect-specific DDL table setups.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if HAS_POSTGRES:
        print("Initializing Supabase/PostgreSQL schema...")
        # Channels Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            platform VARCHAR(50) NOT NULL CHECK (platform IN ('newsletter', 'podcast', 'youtube')),
            raw_url TEXT UNIQUE NOT NULL,
            media_kit_claimed INTEGER NOT NULL DEFAULT 0,
            avatar_url TEXT,
            followers INTEGER DEFAULT 0,
            country VARCHAR(50),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # Sponsors Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sponsors (
            id VARCHAR(50) PRIMARY KEY,
            brand_name VARCHAR(255) UNIQUE NOT NULL,
            industry_tag VARCHAR(100),
            global_website TEXT,
            logo_url TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # Sponsorship Signals Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sponsorship_signals (
            id VARCHAR(50) PRIMARY KEY,
            channel_id VARCHAR(50) NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
            sponsor_id VARCHAR(50) NOT NULL REFERENCES sponsors(id) ON DELETE CASCADE,
            detected_at VARCHAR(100) DEFAULT NULL,
            ad_copy TEXT,
            source_url TEXT,
            estimated_value_tier VARCHAR(50),
            views INTEGER DEFAULT 0,
            transcript TEXT,
            confidence FLOAT DEFAULT 1.0,
            sponsor_type VARCHAR(100),
            estimated_campaign VARCHAR(255),
            product VARCHAR(255),
            cta TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Apply migrations for existing schemas
        alterations = [
            ("channels", "avatar_url", "TEXT"),
            ("channels", "followers", "INTEGER DEFAULT 0"),
            ("channels", "country", "VARCHAR(50)"),
            ("sponsors", "logo_url", "TEXT"),
            ("sponsorship_signals", "views", "INTEGER DEFAULT 0"),
            ("sponsorship_signals", "transcript", "TEXT"),
            ("sponsorship_signals", "confidence", "FLOAT DEFAULT 1.0"),
            ("sponsorship_signals", "sponsor_type", "VARCHAR(100)"),
            ("sponsorship_signals", "estimated_campaign", "VARCHAR(255)"),
            ("sponsorship_signals", "product", "VARCHAR(255)"),
            ("sponsorship_signals", "cta", "TEXT"),
        ]
        for tbl, col, typ in alterations:
            try:
                cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {col} {typ}")
            except Exception as e:
                print(f"PostgreSQL migration warning for {tbl}.{col}: {e}")
                conn.rollback()
                cursor = conn.cursor()
    else:
        print("Initializing Local SQLite schema...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            platform TEXT NOT NULL CHECK (platform IN ('newsletter', 'podcast', 'youtube')),
            raw_url TEXT UNIQUE NOT NULL,
            media_kit_claimed INTEGER NOT NULL DEFAULT 0,
            avatar_url TEXT,
            followers INTEGER DEFAULT 0,
            country TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sponsors (
            id TEXT PRIMARY KEY,
            brand_name TEXT UNIQUE NOT NULL,
            industry_tag TEXT,
            global_website TEXT,
            logo_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sponsorship_signals (
            id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            sponsor_id TEXT NOT NULL,
            detected_at TEXT,
            ad_copy TEXT,
            source_url TEXT,
            estimated_value_tier TEXT,
            views INTEGER DEFAULT 0,
            transcript TEXT,
            confidence REAL DEFAULT 1.0,
            sponsor_type TEXT,
            estimated_campaign TEXT,
            product TEXT,
            cta TEXT,
            FOREIGN KEY (channel_id) REFERENCES channels (id) ON DELETE CASCADE,
            FOREIGN KEY (sponsor_id) REFERENCES sponsors (id) ON DELETE CASCADE
        )
        """)
        
        # Apply migrations for local SQLite
        alterations = [
            ("channels", "avatar_url", "TEXT"),
            ("channels", "followers", "INTEGER DEFAULT 0"),
            ("channels", "country", "TEXT"),
            ("sponsors", "logo_url", "TEXT"),
            ("sponsorship_signals", "views", "INTEGER DEFAULT 0"),
            ("sponsorship_signals", "transcript", "TEXT"),
            ("sponsorship_signals", "confidence", "REAL DEFAULT 1.0"),
            ("sponsorship_signals", "sponsor_type", "TEXT"),
            ("sponsorship_signals", "estimated_campaign", "TEXT"),
            ("sponsorship_signals", "product", "TEXT"),
            ("sponsorship_signals", "cta", "TEXT"),
        ]
        for tbl, col, typ in alterations:
            try:
                cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}")
            except Exception:
                pass
                
    conn.commit()
    
    # Check if empty to seed
    cursor.execute("SELECT COUNT(*) FROM channels")
    count = cursor.fetchone()[0]
    cursor.close()
    
    if count == 0:
        seed_data(conn)
    else:
        conn.close()

def seed_data(conn):
    print("Seeding initial demo data into database...")
    
    channels = [
        ('1', 'TLDR Newsletter', 'newsletter', 'https://tldr.tech', 0, 'https://logo.clearbit.com/tldr.tech', 1250000, 'US'),
        ('2', "Lenny's Podcast", 'podcast', 'https://www.lennyspodcast.com', 1, 'https://api.dicebear.com/7.x/initials/svg?seed=Lenny', 180000, 'US'),
        ('3', 'Fireship', 'youtube', 'https://youtube.com/@fireship', 0, 'https://api.dicebear.com/7.x/initials/svg?seed=Fireship', 3200000, 'US'),
        ('4', 'Superhuman AI Newsletter', 'newsletter', 'https://superhuman.ai', 0, 'https://logo.clearbit.com/superhuman.com', 650000, 'US'),
        ('5', 'Huberman Lab', 'podcast', 'https://hubermanlab.com', 0, 'https://api.dicebear.com/7.x/initials/svg?seed=Huberman', 4500000, 'US'),
        ('6', 'ByteByteGo', 'newsletter', 'https://bytebytego.com', 1, 'https://logo.clearbit.com/bytebytego.com', 550000, 'US'),
        ('7', 'Linus Tech Tips', 'youtube', 'https://youtube.com/@linustechtips', 0, 'https://api.dicebear.com/7.x/initials/svg?seed=Linus', 15600000, 'CA'),
        ('8', 'Syntax.fm', 'podcast', 'https://syntax.fm', 0, 'https://api.dicebear.com/7.x/initials/svg?seed=Syntax', 95000, 'US'),
        ('9', 'The Pragmatic Engineer', 'newsletter', 'https://blog.pragmaticengineer.com', 1, 'https://logo.clearbit.com/pragmaticengineer.com', 480000, 'NL'),
        ('10', 'Lex Fridman Podcast', 'podcast', 'https://lexfridman.com/podcast', 0, 'https://api.dicebear.com/7.x/initials/svg?seed=Lex', 3800000, 'US'),
        ('11', 'MKBHD', 'youtube', 'https://youtube.com/@MKBHD', 0, 'https://api.dicebear.com/7.x/initials/svg?seed=Marques', 18200000, 'US'),
        ('12', "Ben's Bites", 'newsletter', 'https://bensbites.beehiiv.com', 0, 'https://api.dicebear.com/7.x/initials/svg?seed=Ben', 120000, 'UK'),
        ('13', 'All-In Podcast', 'podcast', 'https://allin.com', 0, 'https://api.dicebear.com/7.x/initials/svg?seed=AllIn', 550000, 'US'),
        ('14', 'Theo - t3.gg', 'youtube', 'https://youtube.com/@t3dotgg', 0, 'https://api.dicebear.com/7.x/initials/svg?seed=Theo', 480000, 'US'),
        ('15', 'Morning Brew', 'newsletter', 'https://morningbrew.com', 0, 'https://logo.clearbit.com/morningbrew.com', 4000000, 'US'),
        ('16', 'NetworkChuck', 'youtube', 'https://youtube.com/@NetworkChuck', 0, 'https://api.dicebear.com/7.x/initials/svg?seed=Chuck', 3600000, 'US'),
    ]
    if HAS_POSTGRES:
        query_channels = "INSERT INTO channels (id, name, platform, raw_url, media_kit_claimed, avatar_url, followers, country) VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING"
    else:
        query_channels = "INSERT OR IGNORE INTO channels (id, name, platform, raw_url, media_kit_claimed, avatar_url, followers, country) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    execute_many(conn, query_channels, channels)
    
    sponsors = [
        ('s1', 'Pinecone', 'AI/ML Tools', 'https://pinecone.io', 'https://logo.clearbit.com/pinecone.io'),
        ('s2', 'Retool', 'Dev Platforms', 'https://retool.com', 'https://logo.clearbit.com/retool.com'),
        ('s3', 'Mercury', 'Fintech', 'https://mercury.com', 'https://logo.clearbit.com/mercury.com'),
        ('s4', 'Copy.ai', 'AI/ML Tools', 'https://copy.ai', 'https://logo.clearbit.com/copy.ai'),
        ('s5', 'Vercel', 'Dev Platforms', 'https://vercel.com', 'https://logo.clearbit.com/vercel.com'),
        ('s6', 'Supabase', 'Dev Platforms', 'https://supabase.com', 'https://logo.clearbit.com/supabase.com'),
        ('s7', 'Notion AI', 'AI/ML Tools', 'https://notion.so/ai', 'https://logo.clearbit.com/notion.so'),
        ('s8', 'Stripe', 'Fintech', 'https://stripe.com', 'https://logo.clearbit.com/stripe.com'),
        ('s9', 'NordVPN', 'Consumer Tech', 'https://nordvpn.com', 'https://logo.clearbit.com/nordvpn.com'),
        ('s10', 'Linear', 'Dev Platforms', 'https://linear.app', 'https://logo.clearbit.com/linear.app'),
        ('s11', 'Anthropic', 'AI/ML Tools', 'https://anthropic.com', 'https://logo.clearbit.com/anthropic.com'),
        ('s12', 'Warp', 'Dev Platforms', 'https://warp.dev', 'https://logo.clearbit.com/warp.dev'),
        ('s13', 'Sanity.io', 'Dev Platforms', 'https://sanity.io', 'https://logo.clearbit.com/sanity.io'),
        ('s14', 'Weights & Biases', 'AI/ML Tools', 'https://wandb.ai', 'https://logo.clearbit.com/wandb.ai'),
        ('s15', 'Brex', 'Fintech', 'https://brex.com', 'https://logo.clearbit.com/brex.com'),
        ('s16', 'GitHub Copilot', 'AI/ML Tools', 'https://github.com/features/copilot', 'https://logo.clearbit.com/github.com'),
        ('s17', 'Shopify', 'SaaS / Tech', 'https://shopify.com', 'https://logo.clearbit.com/shopify.com'),
        ('s18', 'Cloudflare', 'Dev Platforms', 'https://cloudflare.com', 'https://logo.clearbit.com/cloudflare.com'),
        ('s19', 'Cursor', 'AI/ML Tools', 'https://cursor.com', 'https://logo.clearbit.com/cursor.com'),
        ('s20', 'Lovable', 'AI/ML Tools', 'https://lovable.dev', 'https://logo.clearbit.com/lovable.dev'),
        ('s21', 'OpenAI', 'AI/ML Tools', 'https://openai.com', 'https://logo.clearbit.com/openai.com'),
        ('s22', 'Perplexity', 'AI/ML Tools', 'https://perplexity.ai', 'https://logo.clearbit.com/perplexity.ai'),
    ]
    if HAS_POSTGRES:
        query_sponsors = "INSERT INTO sponsors (id, brand_name, industry_tag, global_website, logo_url) VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING"
    else:
        query_sponsors = "INSERT OR IGNORE INTO sponsors (id, brand_name, industry_tag, global_website, logo_url) VALUES (?, ?, ?, ?, ?)"
    execute_many(conn, query_sponsors, sponsors)
    
    # Richly detailed deals
    signals = [
        # OpenAI deals
        ('sig1', '14', 's21', '2026-07-03T18:00:00Z', 'OpenAI GPT-4o Developer API promotion.', 'https://youtube.com/watch?v=theo-openai', 'High ($2000+)', 156000, 
         'This video is sponsored by OpenAI. They just released their new GPT-4o model with advanced voice mode. Check out their developer API at openai.com/api to build next-gen intelligence into your apps.', 0.98, 'AI Model Provider', 'GPT-4o API Launch', 'GPT-4o API', 'Go to openai.com/api for developer credits'),
        ('sig2', '3', 's21', '2026-06-25T11:00:00Z', 'OpenAI GPT-4o reasoning push.', 'https://youtube.com/watch?v=fireship-openai', 'High ($2000+)', 480000, 
         'This episode is sponsored by OpenAI. Build on the leading edge of AI with GPT-4o. Access vision, audio transcripts, and text generation via a single, simple API endpoint. Get started at openai.com.', 0.99, 'AI Model Provider', 'GPT-4o Developer Influx', 'GPT-4o Engine', 'Sign up at openai.com'),
         
        # Lovable deals
        ('sig3', '3', 's20', '2026-07-03T10:00:00Z', 'GPT Engineer React app generator.', 'https://youtube.com/watch?v=fireship-lovable', 'High ($2000+)', 520000, 
         'This video is sponsored by Lovable. GPT Engineer by Lovable is the fastest way to build full-stack web apps from a simple text description. It actually writes clean, production-ready React code, sets up your backend, and lets you edit with natural language. Build your next startup app in minutes at lovable.dev.', 0.99, 'AI App Builder', 'GPT Engineer Launch', 'GPT Engineer', 'Go to lovable.dev to build your app'),
        ('sig4', '14', 's20', '2026-06-28T09:00:00Z', 'Lovable.dev code gen capabilities demonstration.', 'https://youtube.com/watch?v=theo-lovable', 'Medium ($500-$2000)', 110000, 
         'This video is sponsored by Lovable. Stop writing boilerplate. Generate real React components and Prisma schemas using Lovable. Go to lovable.dev/theo to start.', 0.97, 'AI App Builder', 'Developer Growth Push', 'Lovable Sandbox', 'Go to lovable.dev/theo'),
         
        # Cursor deals
        ('sig5', '14', 's19', '2026-07-03T12:00:00Z', 'Cursor editor Composer view demo.', 'https://youtube.com/watch?v=theo-cursor', 'High ($2000+)', 125000, 
         'This video is sponsored by Cursor. Cursor is the AI-first code editor built on top of VS Code. It lets you write, edit, and chat with your codebase using Claude 3.5 Sonnet. The Composer feature lets you generate multi-file edits in seconds. Download Cursor for free at cursor.com.', 0.97, 'AI Dev Tools', 'Cursor Composer Promotion', 'Cursor Editor', 'Download for free at cursor.com'),
        ('sig6', '3', 's19', '2026-06-29T14:00:00Z', 'Cursor code editor auto-complete.', 'https://youtube.com/watch?v=fireship-cursor', 'High ($2000+)', 680000, 
         'This video is brought to you by Cursor. Cursor composer allows you to edit multiple files at once. Claude 3.5 Sonnet powers your autocomplete and code chat right in the editor. Download at cursor.sh.', 0.98, 'AI Dev Tools', 'Cursor Code Composer Launch', 'Cursor Editor', 'Download at cursor.sh'),
        ('sig7', '6', 's19', '2026-06-20T08:00:00Z', 'Cursor editor sponsorship on ByteByteGo.', 'https://bytebytego.com/cursor', 'Medium ($500-$2000)', 480000, 
         'This newsletter is sponsored by Cursor. The AI code editor that helps you edit files, write boilerplate, and query code libraries instantly. Try Cursor Pro today.', 0.95, 'AI Dev Tools', 'Niche Newsletter Push', 'Cursor Pro', 'Try Cursor Pro'),

        # Perplexity deals
        ('sig8', '10', 's22', '2026-07-02T14:00:00Z', 'Perplexity Pro AI Search features.', 'https://lexfridman.com/perplexity', 'High ($2000+)', 1800000, 
         'This episode is brought to you by Perplexity. Perplexity is a conversational AI search engine that answers your questions with cited, real-time web references. Skip the list of blue links and get direct answers. Try Perplexity Pro at perplexity.ai.', 0.95, 'AI Search Engine', 'Perplexity Pro Launch', 'Perplexity Pro', 'Use code LEX for Perplexity Pro discount'),
        ('sig9', '2', 's22', '2026-06-24T09:00:00Z', 'Perplexity Search API and answers.', 'https://www.lennyspodcast.com/perplexity', 'Medium ($500-$2000)', 140000, 
         'This episode is sponsored by Perplexity. Access clean conversational search models directly inside your product with the Perplexity API. Try it today.', 0.96, 'AI Search Engine', 'Perplexity API Drive', 'Perplexity API', 'Sign up at perplexity.ai'),
         
        # Notion AI deals
        ('sig10', '2', 's7', '2026-07-03T08:00:00Z', 'Notion AI workspace search.', 'https://lennyspodcast.com/notion', 'Medium ($500-$2000)', 85000, 
         'This episode is sponsored by Notion AI. Stop switching tabs to find information. With Notion AI, you can search across all your workspaces, summarize long docs, and auto-generate project updates in seconds. Get started for free at notion.com/ai.', 0.96, 'AI Productivity', 'Notion Workspace Assistant', 'Notion AI Search', 'Go to notion.com/ai'),
        ('sig11', '4', 's7', '2026-06-19T06:00:00Z', 'Notion AI note-taking templates.', 'https://superhuman.ai/issue-456', 'Medium ($500-$2000)', 650000, 
         'Write faster, brainstorm better, and summarize documents inside your Notion workspace.', 0.94, 'AI Productivity', 'Newsletter Campaign', 'Notion AI Writer', 'Try Notion AI'),
         
        # Vercel deals
        ('sig12', '3', 's5', '2026-06-17T08:00:00Z', 'Vercel static React hosting.', 'https://youtube.com/watch?v=fireship-vercel', 'High ($2000+)', 2000000, 
         'Deploy your next React app globally with zero configuration. Head over to vercel.com/fireship.', 0.99, 'Dev Platforms', 'Fireship Dedicated Sponsorship', 'Vercel Hosting', 'Deploy at vercel.com/fireship'),
         
        # Supabase deals
        ('sig13', '2', 's6', '2026-06-11T12:00:00Z', 'Supabase postgres alternative.', 'https://lennyspodcast.com/ep-supabase', 'Medium ($500-$2000)', 150000, 
         'Supabase is the open-source Firebase alternative. Get started with PostgreSQL databases today.', 0.97, 'Dev Platforms', 'Podcast Ad Slot', 'Supabase Database', 'Create a DB at supabase.com'),
         
        # NordVPN deals
        ('sig14', '7', 's9', '2026-06-18T18:00:00Z', 'NordVPN encryption deals.', 'https://youtube.com/watch?v=ltt-nordvpn', 'Medium ($500-$2000)', 5000000, 
         'Get exclusive NordVPN deals to secure your connection on public Wi-Fi networks.', 0.95, 'Consumer Tech', 'Linus Tech Tips Bundle', 'NordVPN Premium', 'Go to nordvpn.com/ltt'),
        ('sig15', '11', 's9', '2026-06-20T12:00:00Z', 'NordVPN proxy and browser extension.', 'https://youtube.com/watch?v=mkbhd-nordvpn', 'High ($2000+)', 18200000, 
         'NordVPN keeps your browsing private and secure. Use code MKBHD for 2 extra months free.', 0.96, 'Consumer Tech', 'MKBHD Tech Security', 'NordVPN Account', 'Go to nordvpn.com/mkbhd'),
         
        # Stripe deals
        ('sig16', '6', 's8', '2026-07-02T09:00:00Z', 'Stripe checkout API integrations.', 'https://bytebytego.com/stripe', 'High ($2000+)', 500000, 
         'This issue is sponsored by Stripe. From subscription billing to global payment routing, Stripe provides the financial infrastructure for the internet. Start accepting payments in minutes at stripe.com.', 0.98, 'Fintech', 'Global Scale Payments', 'Stripe Billing', 'Register at stripe.com'),
        ('sig17', '15', 's8', '2026-06-25T07:00:00Z', 'Stripe online payments.', 'https://morningbrew.com/stripe', 'High ($2000+)', 4000000, 
         'Stripe powers payments for online business. From startups to public enterprises.', 0.97, 'Fintech', 'Morning Brew Finance Spot', 'Stripe Payment Gateway', 'Register at stripe.com'),

        # Linear deals
        ('sig18', '9', 's10', '2026-06-20T08:00:00Z', 'Linear keyboard shortcuts and sync.', 'https://blog.pragmaticengineer.com/issue-178', 'High ($2000+)', 480000, 
         'Linear is the project and issue tracking tool built for modern engineering teams. Lightning fast, beautifully designed.', 0.99, 'Dev Platforms', 'Pragmatic Engineer Sponsorship', 'Linear Project Tool', 'Sign up at linear.app'),
         
        # Anthropic deals
        ('sig19', '10', 's11', '2026-06-19T14:00:00Z', 'Claude 3.5 Sonnet announcement.', 'https://lexfridman.com/ep-423', 'High ($2000+)', 3800000, 
         'Anthropic is building reliable, interpretable, and steerable AI systems. Check out Claude, our AI assistant.', 0.98, 'AI Model Provider', 'Claude 3.5 Release', 'Claude Sonnet', 'Try Claude at claude.ai'),
         
        # Warp deals
        ('sig20', '14', 's12', '2026-06-17T16:00:00Z', 'Warp terminal AI command search.', 'https://youtube.com/watch?v=t3-warp', 'Medium ($500-$2000)', 480000, 
         'Warp is the terminal reimagined. Built for speed with AI-powered command search. [Promo Codes: THEO]', 0.96, 'Dev Platforms', 'Theo Terminal Sponsor', 'Warp Terminal', 'Download Warp'),
         
        # Cloudflare deals
        ('sig21', '1', 's18', '2026-06-21T10:00:00Z', 'Cloudflare Workers deployment speed.', 'https://tldr.tech/newsletter/2026-06-21', 'High ($2000+)', 1250000, 
         'Cloudflare Workers lets you deploy serverless code globally with millisecond cold starts.', 0.99, 'Dev Platforms', 'TLDR Tech Sponsorship', 'Cloudflare Workers', 'Deploy at cloudflare.com'),
         
        # Shopify deals
        ('sig22', '15', 's17', '2026-06-20T07:00:00Z', 'Shopify merchant checkout.', 'https://morningbrew.com/daily/2026-06-20', 'High ($2000+)', 4000000, 
         'Shopify is the commerce platform powering millions of online stores worldwide.', 0.98, 'SaaS / Tech', 'Morning Brew Daily Spot', 'Shopify Store Builder', 'Go to shopify.com'),
         
        # Sanity.io deals
        ('sig23', '3', 's13', '2026-06-22T08:00:00Z', 'Sanity.io structured data CMS.', 'https://youtube.com/watch?v=fireship-sanity', 'High ($2000+)', 2000000, 
         'Sanity.io provides composable content infrastructure for modern digital experiences.', 0.97, 'Dev Platforms', 'Fireship CMS Review', 'Sanity CMS', 'Try Sanity.io'),
         
        # Weights & Biases deals
        ('sig24', '5', 's14', '2026-06-21T07:00:00Z', 'Weights and Biases model tracking.', 'https://hubermanlab.com/ep-wandb', 'High ($2000+)', 4500000, 
         'Weights & Biases makes machine learning experiment tracking effortless. Track, visualize, and share your ML experiments.', 0.98, 'AI/ML Tools', 'Huberman Science Ad', 'Weights & Biases Platform', 'Go to wandb.ai'),
    ]
    
    if HAS_POSTGRES:
        query_signals = """
        INSERT INTO sponsorship_signals (
            id, channel_id, sponsor_id, detected_at, ad_copy, source_url, estimated_value_tier,
            views, transcript, confidence, sponsor_type, estimated_campaign, product, cta
        ) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 
        ON CONFLICT DO NOTHING
        """
    else:
        query_signals = """
        INSERT OR IGNORE INTO sponsorship_signals (
            id, channel_id, sponsor_id, detected_at, ad_copy, source_url, estimated_value_tier,
            views, transcript, confidence, sponsor_type, estimated_campaign, product, cta
        ) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
    execute_many(conn, query_signals, signals)
    conn.close()

def get_channels():
    conn = get_connection()
    rows = execute_query(conn, "SELECT * FROM channels")
    conn.close()
    return rows

def get_sponsors():
    conn = get_connection()
    rows = execute_query(conn, "SELECT * FROM sponsors")
    conn.close()
    return rows

def get_signals():
    conn = get_connection()
    sql = """
    SELECT sig.*, ch.name as channel_name, ch.platform as channel_platform, ch.avatar_url as channel_avatar, ch.followers as channel_followers, ch.country as channel_country,
           sp.brand_name as sponsor_name, sp.global_website as sponsor_url, sp.logo_url as sponsor_logo
    FROM sponsorship_signals sig
    JOIN channels ch ON sig.channel_id = ch.id
    JOIN sponsors sp ON sig.sponsor_id = sp.id
    ORDER BY sig.detected_at DESC
    """
    rows = execute_query(conn, sql)
    conn.close()
    return rows

def update_channel_claim(channel_id, claimed_bool):
    conn = get_connection()
    execute_write(conn, "UPDATE channels SET media_kit_claimed = ? WHERE id = ?", (1 if claimed_bool else 0, channel_id))
    conn.close()

def save_sponsor_signal(sponsor_name, sponsor_url, source_name, source_platform, ad_copy, detected_at, promo_codes,
                        views=None, transcript=None, confidence=1.0, sponsor_type=None, estimated_campaign=None, product=None, cta=None, followers=None):
    """
    Saves a newly extracted sponsor signal. Automatically creates the sponsor and channel records if they don't exist.
    """
    conn = get_connection()
    
    # 1. Resolve or create Channel ID
    channel_rows = execute_query(conn, "SELECT id FROM channels WHERE name = ?", (source_name,))
    if channel_rows:
        channel_id = channel_rows[0]['id']
        if followers is not None:
            execute_write(conn, "UPDATE channels SET followers = ? WHERE id = ?", (followers, channel_id))
    else:
        import uuid
        channel_id = str(uuid.uuid4())[:8]
        fallback_url = sponsor_url or f"https://{source_name.lower().replace(' ', '')}.com"
        avatar = f"https://api.dicebear.com/7.x/initials/svg?seed={source_name}"
        initial_followers = followers if followers is not None else 0
        execute_write(conn, "INSERT INTO channels (id, name, platform, raw_url, avatar_url, followers, country) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                      (channel_id, source_name, source_platform, fallback_url, avatar, initial_followers, "US"))
        
    # 2. Resolve or create Sponsor ID
    sponsor_rows = execute_query(conn, "SELECT id FROM sponsors WHERE brand_name = ?", (sponsor_name,))
    if sponsor_rows:
        sponsor_id = sponsor_rows[0]['id']
    else:
        import uuid
        sponsor_id = "s_" + str(uuid.uuid4())[:6]
        industry = "AI/ML Tools" if "ai" in sponsor_name.lower() or "gpt" in sponsor_name.lower() else "SaaS / Tech"
        logo = f"https://logo.clearbit.com/{sponsor_url.replace('https://','').replace('http://','').split('/')[0]}" if sponsor_url else None
        execute_write(conn, "INSERT INTO sponsors (id, brand_name, industry_tag, global_website, logo_url) VALUES (?, ?, ?, ?, ?)", 
                      (sponsor_id, sponsor_name, industry, sponsor_url, logo))
        
    # 3. Insert Sponsorship Signal
    import uuid
    signal_id = "sig_" + str(uuid.uuid4())[:6]
    copy_text = ad_copy
    if promo_codes:
        copy_text += f" [Promo Codes: {', '.join(promo_codes)}]"
        
    value_tier = "High ($2000+)" if source_platform == "youtube" else "Medium ($500-$2000)"
    
    execute_write(conn, """
    INSERT INTO sponsorship_signals (
        id, channel_id, sponsor_id, detected_at, ad_copy, source_url, estimated_value_tier,
        views, transcript, confidence, sponsor_type, estimated_campaign, product, cta
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        signal_id, channel_id, sponsor_id, detected_at or datetime.now().isoformat(), ad_copy, sponsor_url, value_tier,
        views or (150000 if source_platform == "youtube" else 30000),
        transcript or copy_text,
        confidence,
        sponsor_type or ("AI Tools" if "ai" in sponsor_name.lower() else "SaaS / Tech"),
        estimated_campaign or "Real-time Live Ingestion",
        product or sponsor_name,
        cta or f"Use promo code to support {source_name}"
    ))
    
    conn.close()
    return signal_id

# Auto-initialize database on loading module
init_db()

if __name__ == "__main__":
    print("Database initialized successfully.")
    print("Channels:", len(get_channels()))
    print("Sponsors:", len(get_sponsors()))
    print("Signals:", len(get_signals()))
