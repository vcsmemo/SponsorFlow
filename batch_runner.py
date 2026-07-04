#!/usr/bin/env python3
"""
SponsorFlow Batch Runner
========================
Orchestrates sponsor signal extraction across podcasts, YouTube channels,
and newsletters by reading curated feed lists and dispatching to the
appropriate collector modules.

Usage:
    python batch_runner.py                          # Process all sources
    python batch_runner.py --source podcast          # Podcasts only
    python batch_runner.py --source youtube           # YouTube only
    python batch_runner.py --source newsletter        # Newsletters only
    python batch_runner.py --dry-run                  # Preview without processing
    python batch_runner.py --limit 5                  # First 5 items per list
    python batch_runner.py --source podcast --limit 3 --dry-run
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve paths relative to this script so it works regardless of cwd
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

FEEDS_PODCASTS = DATA_DIR / "feeds_podcasts.json"
FEEDS_YOUTUBE = DATA_DIR / "feeds_youtube.json"
FEEDS_NEWSLETTERS = DATA_DIR / "feeds_newsletters.json"

# Ensure project root is on sys.path so local modules resolve
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import podcast_collector
import youtube_collector
import database


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

import urllib.request
import re

def get_yt_subs(channel_id):
    url = f"https://www.youtube.com/channel/{channel_id}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        match = re.search(r'\"subscriberCountText\":\{\"accessibility\":\{\"accessibilityData\":\{\"label\":\"([^\"]+)\"\}', html)
        if match:
            text = match.group(1).replace(',', '')
            num_match = re.search(r'([0-9\.]+)([KMBkmb万])?', text)
            if num_match:
                num = float(num_match.group(1))
                suffix = num_match.group(2)
                if suffix in ['M', 'm']: num *= 1000000
                elif suffix in ['K', 'k']: num *= 1000
                elif suffix in ['B', 'b']: num *= 1000000000
                elif suffix == '万': num *= 10000
                return int(num)
        return 0
    except Exception:
        return 0


def load_json_feed(path: Path) -> list:
    """Load and return a JSON array from *path*, or an empty list on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            print(f"  ⚠  Expected a JSON array in {path.name}, got {type(data).__name__}")
            return []
        return data
    except FileNotFoundError:
        print(f"  ✗  Feed file not found: {path}")
        return []
    except json.JSONDecodeError as exc:
        print(f"  ✗  Invalid JSON in {path.name}: {exc}")
        return []


def save_signals(signals, source_name: str, source_platform: str, followers=None):
    """Persist a list of SponsorSignal objects via database.save_sponsor_signal."""
    saved = 0
    for sig in signals:
        try:
            database.save_sponsor_signal(
                sponsor_name=sig.sponsor_name,
                sponsor_url=sig.sponsor_url,
                source_name=source_name,
                source_platform=source_platform,
                ad_copy=sig.ad_copy_summary,
                detected_at=datetime.now().isoformat(),
                promo_codes=sig.detected_promo_codes,
                followers=followers
            )
            saved += 1
        except Exception as exc:
            print(f"      ⚠  DB save failed for '{sig.sponsor_name}': {exc}")
    return saved


# ---------------------------------------------------------------------------
# Source processors
# ---------------------------------------------------------------------------

def process_podcasts(feeds: list, *, dry_run: bool = False, delay: float = 1.5):
    """Iterate over podcast feeds and extract sponsor signals."""
    total = len(feeds)
    total_signals = 0
    errors = 0

    for idx, feed in enumerate(feeds, start=1):
        name = feed.get("name", "Unknown")
        url = feed.get("rss_url", "")
        category = feed.get("category", "")
        print(f"\n🎙  Processing {idx}/{total} podcasts — {name}  [{category}]")

        if dry_run:
            print(f"   [DRY-RUN] Would fetch RSS: {url}")
            continue

        try:
            signals = podcast_collector.process_feed(url)
            count = save_signals(signals, source_name=name, source_platform="podcast")
            total_signals += count
            print(f"   ✓ Saved {count} sponsor signal(s)")
        except Exception as exc:
            errors += 1
            print(f"   ✗ Error: {exc}")

        if idx < total:
            time.sleep(delay)

    return total_signals, errors


def process_youtube(feeds: list, *, dry_run: bool = False, delay: float = 2.0):
    """Iterate over YouTube channels and extract sponsor signals."""
    total = len(feeds)
    total_signals = 0
    errors = 0

    for idx, feed in enumerate(feeds, start=1):
        name = feed.get("name", "Unknown")
        channel_id = feed.get("channel_id", "")
        category = feed.get("category", "")
        print(f"\n📺  Processing {idx}/{total} YouTube channels — {name}  [{category}]")

        if dry_run:
            print(f"   [DRY-RUN] Would process channel: {channel_id}")
            continue

        try:
            followers = get_yt_subs(channel_id)
            signals = youtube_collector.process_youtube_channel(channel_id)
            count = save_signals(signals, source_name=name, source_platform="youtube", followers=followers)
            total_signals += count
            print(f"   ✓ Saved {count} sponsor signal(s)")
        except Exception as exc:
            errors += 1
            print(f"   ✗ Error: {exc}")

        if idx < total:
            time.sleep(delay)

    return total_signals, errors


def process_newsletters(feeds: list, *, dry_run: bool = False, delay: float = 1.0):
    """
    Iterate over newsletters. Newsletter collection is not yet automated
    (no newsletter_collector module), so this logs what would be processed
    and is ready for future integration.
    """
    total = len(feeds)

    for idx, feed in enumerate(feeds, start=1):
        name = feed.get("name", "Unknown")
        archive_url = feed.get("archive_url", "")
        category = feed.get("category", "")
        print(f"\n📧  Processing {idx}/{total} newsletters — {name}  [{category}]")

        if dry_run:
            print(f"   [DRY-RUN] Would scrape archive: {archive_url}")
            continue

        # TODO: Integrate newsletter_collector.process_archive(archive_url)
        # once the module is implemented. For now, just log the intent.
        print(f"   ⏭  Skipped (newsletter_collector not yet implemented)")
        print(f"      Archive URL: {archive_url}")

        if idx < total:
            time.sleep(delay)

    return 0, 0  # signals, errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="SponsorFlow Batch Runner — bulk-process podcast, YouTube, and newsletter feeds.",
    )
    parser.add_argument(
        "--source",
        choices=["podcast", "youtube", "newsletter", "all"],
        default="all",
        help="Which source type to process (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be processed without making any API calls",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N items from each feed list (useful for testing)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    run_start = datetime.now()

    print("=" * 64)
    print("  SponsorFlow Batch Runner")
    print(f"  Started at {run_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Source: {args.source}  |  Limit: {args.limit or 'all'}  |  Dry-run: {args.dry_run}")
    print("=" * 64)

    grand_signals = 0
    grand_errors = 0

    # --- Podcasts ---
    if args.source in ("podcast", "all"):
        print("\n" + "─" * 40)
        print("  📻  PODCASTS")
        print("─" * 40)
        feeds = load_json_feed(FEEDS_PODCASTS)
        if args.limit:
            feeds = feeds[: args.limit]
        print(f"  Loaded {len(feeds)} podcast feed(s)")
        signals, errors = process_podcasts(feeds, dry_run=args.dry_run)
        grand_signals += signals
        grand_errors += errors

    # --- YouTube ---
    if args.source in ("youtube", "all"):
        print("\n" + "─" * 40)
        print("  📺  YOUTUBE CHANNELS")
        print("─" * 40)
        feeds = load_json_feed(FEEDS_YOUTUBE)
        if args.limit:
            feeds = feeds[: args.limit]
        print(f"  Loaded {len(feeds)} YouTube channel(s)")
        signals, errors = process_youtube(feeds, dry_run=args.dry_run)
        grand_signals += signals
        grand_errors += errors

    # --- Newsletters ---
    if args.source in ("newsletter", "all"):
        print("\n" + "─" * 40)
        print("  📧  NEWSLETTERS")
        print("─" * 40)
        feeds = load_json_feed(FEEDS_NEWSLETTERS)
        if args.limit:
            feeds = feeds[: args.limit]
        print(f"  Loaded {len(feeds)} newsletter(s)")
        signals, errors = process_newsletters(feeds, dry_run=args.dry_run)
        grand_signals += signals
        grand_errors += errors

    # --- Summary ---
    run_end = datetime.now()
    elapsed = (run_end - run_start).total_seconds()
    print("\n" + "=" * 64)
    print("  BATCH RUN COMPLETE")
    print(f"  Signals saved : {grand_signals}")
    print(f"  Errors        : {grand_errors}")
    print(f"  Duration      : {elapsed:.1f}s")
    print(f"  Finished at   : {run_end.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 64)


if __name__ == "__main__":
    main()
