import os
import requests
from datetime import datetime, timedelta
import json

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
TELEGRAM_TOKEN = "8212896282:AAHllkETjlCa94yu-MDukQlh5iHp-LiuzXg"
CHAT_ID = "-1003992190647"

KEYWORDS = ["BlancVPN", "https://blanc.link/"]

VIDEO_LIMIT = 200
RECENT_DAYS = 7

SEEN_FILE = "seen_videos.json"

CHANNELS = [
    {"name": "Kolezev", "id": "UCLxr1ACVGlrUvpGkc_ruMKg"},
    {"name": "vdud", "id": "UCMCgOm8GZkHp8zJ6l7_hIuA"},
    {"name": "Max Katz", "id": "UCUGfDbfRIx51kJGGHIFo8Rw"},
]

def load_seen():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_seen(data):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def safe_get(url, params):
    try:
        r = requests.get(url, params=params, timeout=30)
        return r.json()
    except:
        return {}

def get_video_ids(channel_id):
    ids = []
    next_page = None

    while len(ids) < VIDEO_LIMIT:
        data = safe_get(
            "https://www.googleapis.com/youtube/v3/search",
            {
                "key": YOUTUBE_API_KEY,
                "channelId": channel_id,
                "part": "id",
                "order": "date",
                "maxResults": 50,
                "type": "video",
                "pageToken": next_page
            }
        )

        for item in data.get("items", []):
            vid = item.get("id", {}).get("videoId")
            if vid:
                ids.append(vid)

        next_page = data.get("nextPageToken")
        if not next_page:
            break

    return ids

def get_details(ids):
    videos = []

    for i in range(0, len(ids), 50):
        batch = ids[i:i+50]

        data = safe_get(
            "https://www.googleapis.com/youtube/v3/videos",
            {
                "key": YOUTUBE_API_KEY,
                "id": ",".join(batch),
                "part": "snippet"
            }
        )

        for item in data.get("items", []):
            s = item["snippet"]
            videos.append({
                "id": item["id"],
                "title": s["title"],
                "desc": s["description"],
                "date": s["publishedAt"]
            })

    return videos

def send(msg):
    requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        params={"chat_id": CHAT_ID, "text": msg}
    )

def is_recent(date_str):
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt > datetime.utcnow() - timedelta(days=RECENT_DAYS)
    except:
        return False

def main():
    seen = load_seen()

    for ch in CHANNELS:
        print("канал:", ch["name"])

        ids = get_video_ids(ch["id"])
        videos = get_details(ids)

        for v in videos:
            vid = v["id"]
            desc = v["desc"].lower()

            if not any(k.lower() in desc for k in KEYWORDS):
                continue

            # ключевой фикс:
            last_sent = seen.get(vid)

            # если уже отправляли и видео не свежее → пропускаем
            if last_sent and not is_recent(v["date"]):
                continue

            msg = f"{v['title']}\nhttps://youtube.com/watch?v={vid}"
            send(msg)

            # записываем время отправки
            seen[vid] = datetime.utcnow().isoformat()

    save_seen(seen)

if __name__ == "__main__":
    main()
