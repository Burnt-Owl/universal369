"""
Publish Agent — uploads final video to YouTube Shorts and TikTok.
Output: appends to runs/publish-log.json
"""

import json
import time
import anthropic
import requests
from datetime import datetime, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    YOUTUBE_CLIENT_SECRETS,
    TIKTOK_ACCESS_TOKEN,
    MAX_RETRIES,
    RETRY_DELAYS,
)

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    import google.oauth2.credentials
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False


TITLE_PROMPT = """You write YouTube Shorts and TikTok titles and descriptions for a comedy series called "Raven & Jax" — a tattooed couple on their couch reacting to world events.
She's conspiracy-smart, he's lovably clueless.

Rules:
- Title: Max 60 chars, punchy, reference the couple + the event
- Description: 2-3 sentences. Mention the event. End with "New drop daily."
- Hashtags: #ravenjax #couplereacts #worldnews + 3-5 relevant topic hashtags

Return JSON: {"title": "...", "description": "...", "hashtags": ["...", "..."]}"""


def generate_metadata(headline: str, script_summary: str) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    user_msg = f"Today's event: {headline}\nScript vibe: {script_summary}\n\nGenerate title, description, hashtags."

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        system=TITLE_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def upload_youtube(video_file: Path, title: str, description: str, tags: list[str]) -> str:
    if not YOUTUBE_AVAILABLE:
        raise ImportError("google-api-python-client not installed")
    if not YOUTUBE_CLIENT_SECRETS:
        raise ValueError("YOUTUBE_CLIENT_SECRETS not set")

    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    flow = InstalledAppFlow.from_client_secrets_file(YOUTUBE_CLIENT_SECRETS, scopes)
    credentials = flow.run_local_server(port=0)

    youtube = build("youtube", "v3", credentials=credentials)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": "23",  # Comedy
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_file), mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"[publish_agent] YouTube upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    return f"https://youtu.be/{video_id}"


def upload_tiktok(video_file: Path, title: str) -> str:
    """Upload to TikTok via Content Posting API v2."""
    if not TIKTOK_ACCESS_TOKEN:
        raise ValueError("TIKTOK_ACCESS_TOKEN not set")

    headers = {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    # Step 1: Initialize upload
    init_resp = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers=headers,
        json={
            "post_info": {
                "title": title[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_file.stat().st_size,
                "chunk_size": video_file.stat().st_size,
                "total_chunk_count": 1,
            },
        },
        timeout=30,
    )
    init_resp.raise_for_status()
    data = init_resp.json()["data"]
    publish_id = data["publish_id"]
    upload_url = data["upload_url"]

    # Step 2: Upload video bytes
    with open(video_file, "rb") as f:
        video_bytes = f.read()

    upload_resp = requests.put(
        upload_url,
        data=video_bytes,
        headers={
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{len(video_bytes)-1}/{len(video_bytes)}",
        },
        timeout=120,
    )
    upload_resp.raise_for_status()

    return f"https://www.tiktok.com/ (publish_id: {publish_id})"


def run(run_dir: Path, dry_run: bool = False) -> dict:
    event_data = json.loads((run_dir / "selected-event.json").read_text())
    headline = event_data["selected"]["headline"]

    script_lines = (run_dir / "script.md").read_text().split("\n")
    script_summary = " ".join(
        l.split(":", 1)[1].strip()
        for l in script_lines
        if l.startswith(("RAVEN:", "JAX:"))
    )[:200]

    video_file = next(run_dir.glob("final-*.mp4"), None)
    if not video_file:
        raise FileNotFoundError(f"No final video found in {run_dir}")

    print("[publish_agent] Generating title and description...")
    meta = generate_metadata(headline, script_summary)
    title = meta["title"]
    description = meta["description"] + "\n\n" + " ".join(f"#{t}" for t in meta["hashtags"])
    tags = meta["hashtags"]

    result = {
        "date": run_dir.name,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "title": title,
        "video_file": str(video_file),
        "youtube_url": None,
        "tiktok_url": None,
        "dry_run": dry_run,
    }

    if dry_run:
        print(f"[publish_agent] DRY RUN — would publish: \"{title}\"")
        return result

    # YouTube
    try:
        print("[publish_agent] Uploading to YouTube Shorts...")
        yt_url = upload_youtube(video_file, title, description, tags)
        result["youtube_url"] = yt_url
        print(f"[publish_agent] YouTube: {yt_url}")
    except Exception as e:
        print(f"[publish_agent] YouTube upload failed: {e}")

    # TikTok
    try:
        print("[publish_agent] Uploading to TikTok...")
        tt_url = upload_tiktok(video_file, title)
        result["tiktok_url"] = tt_url
        print(f"[publish_agent] TikTok: {tt_url}")
    except Exception as e:
        print(f"[publish_agent] TikTok upload failed: {e}")

    # Log
    log_file = run_dir.parent / "publish-log.json"
    log = json.loads(log_file.read_text()) if log_file.exists() else []
    log.append(result)
    log_file.write_text(json.dumps(log, indent=2))

    return result


if __name__ == "__main__":
    from datetime import date
    run_dir = Path(__file__).parent.parent / "runs" / date.today().isoformat()
    run(run_dir, dry_run=True)
