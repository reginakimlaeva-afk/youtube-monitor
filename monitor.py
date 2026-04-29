import os
import requests
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

# ===== НАСТРОЙКИ =====
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
TELEGRAM_TOKEN = "8212896282:AAHllkETjlCa94yu-MDukQlh5iHp-LiuzXg"
CHAT_ID = "-1003992190647"

KEYWORDS = ["BlancVPN", "https://blanc.link/"]

VIDEO_LIMIT_API = 200        # сколько брать через API (search)
RECENT_DAYS = 7              # сколько дней считать "недавними" (перепроверка)
SEEN_FILE = "seen_videos.txt"

CHANNELS = [
    {"name": "Kolezev", "id": "UCLxr1ACVGlrUvpGkc_ruMKg"},
    {"name": "vdud", "id": "UCMCgOm8GZkHp8zJ6l7_hIuA"},
    {"name": "Max Katz", "id": "UCUGfDbfRIx51kJGGHIFo8Rw"},
    # добавляй остальные при необходимости
]

# ===== ХРАНЕНИЕ =====
def load_seen():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except:
        return set()

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        for vid in sorted(seen):
            f.write(vid + "\n")

# ===== ВСПОМОГАТЕЛЬНОЕ =====
def safe_get(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=30)
        data = r.json()
        if "error" in data:
            print("API error:", data["error"])
            return {}
        return data
    except:
        return {}

def send(msg):
    try:
        requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            params={"chat_id": CHAT_ID, "text": msg},
            timeout=30
        )
    except:
        pass

def is_recent(date_str):
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt > datetime.utcnow() - timedelta(days=RECENT_DAYS)
    except:
        return False

def format_date(date_str):
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y")
    except:
        return "?"

# ===== RSS (ловит быстрее, чем API) =====
def get_ids_from_rss(channel_id):
    ids = []
    try:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        r = requests.get(url, timeout=30)
        root = ET.fromstring(r.text)

        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            vid = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId")
            if vid is not None:
                ids.append(vid.text)
    except:
        pass

    return ids

# ===== API (глубокий сбор) =====
def get_ids_from_api(channel_id):
    ids = []
    next_page = None

    while len(ids) < VIDEO_LIMIT_API:
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

def get_video_details(video_ids):
    videos = []

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]

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
                "title": s.get("title", ""),
                "desc": s.get("description", ""),
                "date": s.get("publishedAt", "")
            })

    return videos

# ===== ОСНОВНАЯ ЛОГИКА =====
def main():
    if not YOUTUBE_API_KEY:
        print("Нет YOUTUBE_API_KEY")
        return

    seen = load_seen()
    print("seen:", len(seen))

    for ch in CHANNELS:
        print("канал:", ch["name"])

        # комбинируем RSS + API
        ids = []
        ids += get_ids_from_rss(ch["id"])
        ids += get_ids_from_api(ch["id"])

        # убираем дубли
        ids = list(dict.fromkeys(ids))

        videos = get_video_details(ids)

        for v in videos:
            vid = v["id"]
            desc = v["desc"].lower()

            # проверка ключевых слов (и по отдельности, и вместе)
            if not any(k.lower() in desc for k in KEYWORDS):
                continue

            # анти-дубли + перепроверка недавних
            if vid in seen and not is_recent(v["date"]):
                continue

            msg = (
                f"BlancVPN найден\n\n"
                f"{v['title']}\n"
                f"{format_date(v['date'])}\n"
                f"https://youtube.com/watch?v={vid}"
            )

            send(msg)
            seen.add(vid)
            print("отправлено:", v["title"])

    save_seen(seen)

if __name__ == "__main__":
    main()
