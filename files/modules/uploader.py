"""
uploader.py
Handles uploads to YouTube Shorts and Instagram Reels.
YouTube  → official Google Data API v3 (needs one-time OAuth2 setup)
Instagram → instagrapi (unofficial but widely used)
"""

import os
import json
import time
import random
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  YOUTUBE
# ─────────────────────────────────────────────────────────────────────────────

def _build_youtube_service(client_secret_file: str, token_file: str):
    """Build (and cache) the YouTube API client with OAuth2."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(video_path: str, title: str, description: str,
                      client_secret_file: str, token_file: str) -> dict:
    """Upload an MP4 as a YouTube Short. Returns the API response."""
    from googleapiclient.http import MediaFileUpload

    service = _build_youtube_service(client_secret_file, token_file)

    body = {
        "snippet": {
            "title": title[:100],           # YouTube 100-char limit
            "description": description,
            "tags": ["shorts", "viral", "facts", "trending"],
            "categoryId": "22",             # People & Blogs
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "madeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True,
                            mimetype="video/mp4")

    logger.info(f"📤 Uploading to YouTube: {title}")
    request = service.videos().insert(
        part=",".join(body.keys()), body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info(f"   YouTube upload {int(status.progress()*100)}%…")

    video_id = response.get("id", "unknown")
    url = f"https://www.youtube.com/shorts/{video_id}"
    logger.info(f"✅ YouTube upload done → {url}")
    return {"id": video_id, "url": url}


# ─────────────────────────────────────────────────────────────────────────────
#  INSTAGRAM  (Meta Graph API — official, no login challenges)
# ─────────────────────────────────────────────────────────────────────────────

def _upload_to_cloudinary(video_path: str, cloud_name: str, api_key: str, api_secret: str) -> str:
    """Upload video to Cloudinary and return public URL."""
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)
    logger.info("☁️  Uploading to Cloudinary…")
    result = cloudinary.uploader.upload(video_path, resource_type="video",
                                        folder="autoshorts")
    url = result["secure_url"]
    logger.info(f"☁️  Cloudinary URL: {url}")
    return url


def upload_to_instagram(video_path: str, caption: str,
                        user_id: str, access_token: str,
                        cloud_name: str, api_key: str, api_secret: str) -> dict:
    """Upload video as an Instagram Reel using the official Graph API."""
    import requests as req

    # Step 1: Upload to Cloudinary to get public URL
    video_url = _upload_to_cloudinary(video_path, cloud_name, api_key, api_secret)

    base = "https://graph.instagram.com/v19.0"
    logger.info("📤 Creating Instagram Reel container…")

    # Create container
    r = req.post(f"{base}/{user_id}/media", data={
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": access_token,
    })

    data = r.json()
    if "id" not in data:
        raise Exception(f"Container creation failed: {data}")

    container_id = data["id"]
    logger.info(f"📦 Container created: {container_id}")

    # Step 2: Wait for container to be ready
    for _ in range(20):
        time.sleep(5)
        status = req.get(f"{base}/{container_id}", params={
            "fields": "status_code",
            "access_token": access_token,
        }).json()
        code = status.get("status_code", "")
        logger.info(f"⏳ Container status: {code}")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise Exception(f"Container processing failed: {status}")

    # Step 3: Publish
    pub = req.post(f"{base}/{user_id}/media_publish", data={
        "creation_id": container_id,
        "access_token": access_token,
    })
    pub_data = pub.json()
    if "id" not in pub_data:
        raise Exception(f"Publish failed: {pub_data}")

    media_id = pub_data["id"]
    url = f"https://www.instagram.com/reel/{media_id}/"
    logger.info(f"✅ Instagram upload done → {url}")

    # Auto-delete from Cloudinary to save space
    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)
        public_id = video_url.split("/upload/")[1].split(".")[0]
        # Remove version prefix if present
        parts = public_id.split("/")
        if parts[0].startswith("v"):
            public_id = "/".join(parts[1:])
        cloudinary.uploader.destroy(public_id, resource_type="video")
        logger.info(f"🗑️  Cloudinary video deleted")
    except Exception as e:
        logger.warning(f"Cloudinary delete failed: {e}")

    return {"id": media_id, "url": url}


# ─────────────────────────────────────────────────────────────────────────────
#  UNIFIED UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

def upload_everywhere(video_path: str, topic: str, description: str,
                      ig_caption: str, cfg: dict,
                      youtube_only: bool = False) -> dict:
    results = {"youtube": None, "instagram": None, "timestamp": datetime.now().isoformat()}

    # ── YouTube ──────────────────────────────────────────────────────────────
    try:
        title = f"{topic.title()} #Shorts"
        yt = upload_to_youtube(
            video_path=video_path,
            title=title,
            description=description,
            client_secret_file=cfg["YOUTUBE_CLIENT_SECRET_FILE"],
            token_file=cfg["YOUTUBE_TOKEN_FILE"],
        )
        results["youtube"] = yt
    except Exception as e:
        logger.error(f"❌ YouTube upload failed: {e}")
        results["youtube"] = {"error": str(e)}

    if youtube_only:
        return results

    time.sleep(random.uniform(5, 15))

    # ── Instagram ────────────────────────────────────────────────────────────
    try:
        ig = upload_to_instagram(
            video_path=video_path,
            caption=ig_caption,
            user_id=cfg["INSTAGRAM_USER_ID"],
            access_token=cfg["INSTAGRAM_ACCESS_TOKEN"],
            cloud_name=cfg["CLOUDINARY_CLOUD_NAME"],
            api_key=cfg["CLOUDINARY_API_KEY"],
            api_secret=cfg["CLOUDINARY_API_SECRET"],
        )
        results["instagram"] = ig
    except Exception as e:
        logger.error(f"❌ Instagram upload failed: {e}")
        results["instagram"] = {"error": str(e)}

    return results


def upload_pov(video_path: str, title: str, body: str, cfg: dict) -> dict:
    """Upload POV video to both YouTube Shorts + Instagram Reels."""
    results = {"youtube": None, "instagram": None, "timestamp": datetime.now().isoformat()}

    caption = f"{title}\n\n{body}\n\n#pov #emotional #relatable #fyp #foryou #viral #shorts"

    # YouTube
    try:
        yt = upload_to_youtube(
            video_path=video_path,
            title=f"{title} #Shorts",
            description=caption,
            client_secret_file=cfg["YOUTUBE_CLIENT_SECRET_FILE"],
            token_file=cfg["YOUTUBE_TOKEN_FILE"],
        )
        results["youtube"] = yt
        logger.info(f"✅ POV YouTube → {yt['url']}")
    except Exception as e:
        logger.error(f"❌ POV YouTube failed: {e}")
        results["youtube"] = {"error": str(e)}

    time.sleep(random.uniform(5, 15))

    # Instagram
    try:
        ig = upload_to_instagram(
            video_path=video_path,
            caption=caption,
            user_id=cfg["INSTAGRAM_USER_ID"],
            access_token=cfg["INSTAGRAM_ACCESS_TOKEN"],
            cloud_name=cfg["CLOUDINARY_CLOUD_NAME"],
            api_key=cfg["CLOUDINARY_API_KEY"],
            api_secret=cfg["CLOUDINARY_API_SECRET"],
        )
        results["instagram"] = ig
        logger.info(f"✅ POV Instagram → {ig['url']}")
    except Exception as e:
        logger.error(f"❌ POV Instagram failed: {e}")
        results["instagram"] = {"error": str(e)}

    return results