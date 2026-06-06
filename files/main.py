"""
main.py  — Auto Shorts Bot Orchestrator
Run this once:  python main.py
It will run forever, posting videos on schedule.
"""

import sys
import os
import json
import time
import logging
import random
import schedule
from datetime import datetime, date
from pathlib import Path

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(__file__))

import config
from modules.trend_finder  import get_trending_topics, pick_niche_for_topic
from modules.script_writer import write_script, write_description
from modules.video_maker   import build_video
from modules.uploader      import upload_everywhere

# ─────────────────────────────────────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────────────────────────────────────

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  ACTIVITY LOG  (JSON, read by the dashboard)
# ─────────────────────────────────────────────────────────────────────────────

def _read_log() -> dict:
    try:
        with open(config.LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"posts": [], "stats": {"total": 0, "today": 0, "last_run": None}}


def _write_log(data: dict):
    os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
    with open(config.LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _log_post(topic: str, niche: str, video_path: str, upload_result: dict):
    data = _read_log()
    entry = {
        "id":         len(data["posts"]) + 1,
        "timestamp":  datetime.now().isoformat(),
        "topic":      topic,
        "niche":      niche,
        "video":      video_path,
        "youtube":    upload_result.get("youtube"),
        "instagram":  upload_result.get("instagram"),
    }
    data["posts"].insert(0, entry)       # newest first
    data["posts"] = data["posts"][:100]  # keep last 100

    today_str = date.today().isoformat()
    data["stats"]["total"] += 1
    data["stats"]["today"]  = sum(
        1 for p in data["posts"]
        if p["timestamp"].startswith(today_str)
    )
    data["stats"]["last_run"] = datetime.now().isoformat()
    _write_log(data)


# ─────────────────────────────────────────────────────────────────────────────
#  GARBAGE COLLECTOR
# ─────────────────────────────────────────────────────────────────────────────

def _cleanup(video_path: str):
    """Delete rendered MP4 and all cached Pexels clips after upload."""
    freed = 0

    # Delete the rendered output video
    if video_path and os.path.exists(video_path):
        size = os.path.getsize(video_path)
        os.remove(video_path)
        freed += size
        logger.info(f"🗑️  Deleted output: {os.path.basename(video_path)}")

    # Delete all cached Pexels clips
    pexels_cache = os.path.join("assets", "videos")
    if os.path.isdir(pexels_cache):
        for f in os.listdir(pexels_cache):
            fp = os.path.join(pexels_cache, f)
            if os.path.isfile(fp):
                size = os.path.getsize(fp)
                os.remove(fp)
                freed += size
        logger.info(f"🗑️  Cleared Pexels cache — freed {freed / 1024 / 1024:.1f} MB")


# ─────────────────────────────────────────────────────────────────────────────
#  CORE PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def make_and_post_one_video():
    """Full pipeline: trend → script → video → upload."""
    logger.info("━" * 60)
    logger.info("🚀 Starting pipeline…")

    # 1. Pick a topic
    topics = get_trending_topics(count=5)
    topic  = random.choice(topics)
    niche  = pick_niche_for_topic(topic)
    logger.info(f"📌 Topic: {topic}  |  Niche: {niche}")

    # 2. Write script
    script = write_script(topic, niche)
    logger.info(f"📝 Script:\n{script[:200]}…")

    # 3. Render video
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in topic)[:40]
    ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = os.path.join(config.OUTPUT_DIR, f"{ts}_{safe_name}.mp4")

    build_video(
        topic=topic,
        script=script,
        niche=niche,
        output_path=video_path,
        voice=config.TTS_VOICE,
        pexels_key=config.PEXELS_API_KEY,
    )

    # 4. Build captions
    yt_description = write_description(topic, config.HASHTAGS_YOUTUBE)
    ig_caption     = f"{topic.title()}\n\n{config.HASHTAGS_INSTAGRAM}"

    # 5. Upload — YouTube only (Instagram handled by POV bot)
    result = upload_everywhere(
        video_path=video_path,
        topic=topic,
        description=yt_description,
        ig_caption=None,
        cfg=vars(config),
        youtube_only=True,
    )

    # 6. Log
    _log_post(topic, niche, video_path, result)

    yt_url = (result.get("youtube") or {}).get("url", "N/A")
    ig_url = (result.get("instagram") or {}).get("url", "N/A")
    logger.info(f"🎉 Done!  YouTube: {yt_url}  |  Instagram: {ig_url}")

    # 7. Cleanup — delete rendered video + cached Pexels clips to free space
    _cleanup(video_path)

    logger.info("━" * 60)


# ─────────────────────────────────────────────────────────────────────────────
#  SCHEDULER
# ─────────────────────────────────────────────────────────────────────────────

def _schedule_daily_posts():
    """
    Schedule VIDEOS_PER_DAY posts evenly across the day (8 AM – 10 PM).
    Adds ±15 min jitter so posts don't look robotic.
    """
    schedule.clear()

    n = config.VIDEOS_PER_DAY
    start_h, end_h = 8, 22
    span = end_h - start_h

    for i in range(n):
        base_hour   = start_h + int((i + 0.5) * span / n)
        base_min    = random.randint(-15, 15)        # ±15 min jitter
        total_min   = base_hour * 60 + base_min
        total_min   = max(start_h * 60, min(end_h * 60, total_min))
        h, m        = divmod(total_min, 60)
        time_str    = f"{h:02d}:{m:02d}"
        schedule.every().day.at(time_str).do(make_and_post_one_video)
        logger.info(f"⏰ Scheduled post #{i+1} at {time_str}")

    # Re-schedule every midnight so jitter changes daily
    schedule.every().day.at("00:01").do(_schedule_daily_posts)


def run():
    logger.info("=" * 60)
    logger.info("  AUTO SHORTS BOT  —  starting up")
    logger.info(f"  Posting {config.VIDEOS_PER_DAY} video(s) per day")
    logger.info(f"  Niches: {', '.join(config.NICHES)}")
    logger.info("=" * 60)

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    _schedule_daily_posts()

    # Optional: post one immediately on first start (remove if unwanted)
    if "--now" in sys.argv:
        logger.info("--now flag detected, posting immediately…")
        make_and_post_one_video()

    logger.info("🤖 Bot is running. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    run()