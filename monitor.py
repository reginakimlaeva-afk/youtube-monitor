import re
import os
import requests
from datetime import datetime

YOUTUBE_API_KEY = "AIzaSyBEQXQN8IRngxmluniVomypIom3yfGPIVg"
TELEGRAM_TOKEN = "8212896282:AAHllkETjlCa94yu-MDukQlh5iHp-LiuzXg"
CHAT_ID = "-1003992190647"

KEYWORDS = ["https"]
VIDEO_LIMIT_PER_CHANNEL = 30
SEEN_FILE = "seen_videos.txt"

CHANNEL_URLS = [
    "https://www.youtube.com/@Max_Katz",
    "https://www.youtube.com/@vdud",
    "https://www.youtube.com/@Kolezev",
    "https://www.youtube.com/@Web3nity",
    "https://www.youtube.com/@RuslanBelyy",
    "https://www.youtube.com/@VadimKey",
    "https://www.youtube.com/@skazhigordeevoy",
    "https://www.youtube.com/@Zhukova_PS",
    "https://www.youtube.com/@Spoontamer",
    "https://www.youtube.com/@MackNack",
    "https://www.youtube.com/@varlamov",
    "https://www.youtube.com/@Ekaterina_Schulmann",
    "https://www.youtube.com/@radiodolin",
    "https://www.youtube.com/@vraevskiy",
    "https://www.youtube.com/@AlexShevstsov"
]

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def mark_seen(video_id):
    with open(SEEN_FILE, "a", encoding="utf-8") as f:
        f.write(video_id + "\n")

def safe_get(url, params=None):
    try:
        return requests.get(url, params=params, timeout=30).json()
    except Exception as e:
        print("Ошибка запроса:", e)
        return {}

def format_date(youtube_date):
    try:
        dt = datetime.fromisoformat(youtube_date.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y")
    except:
        return "не указана"

def get_handle(url):
    m = re.search(r"@([^/?]+)", url)
    return m.group(1) if m else None

def get_channel_id(url):
    handle = get_handle(url)
    if not handle:
        return None

    data = safe_get(
        "https://www.googleapis.com/youtube/v3/channels",
        {"key": YOUTUBE_API_KEY, "part": "id", "forHandle": handle}
    )

    items = data.get("items", [])
    return items[0]["id"] if items else None

def get_channel_info(channel_id):
    data = safe_get(
        "https://www.googleapis.com/youtube/v3/channels",
        {"key": YOUTUBE_API_KEY, "id": channel_id, "part": "snippet,contentDetails"}
    )

    items = data.get("items", [])
    if not items:
        return None

    item = items[0]
    return item["snippet"]["title"], item["contentDetails"]["relatedPlaylists"]["uploads"]

def get_ids_playlist(playlist_id):
    data = safe_get(
        "https://www.googleapis.com/youtube/v3/playlistItems",
        {
            "key": YOUTUBE_API_KEY,
            "playlistId": playlist_id,
            "part": "contentDetails",
            "maxResults": VIDEO_LIMIT_PER_CHANNEL
        }
    )

    return [i["contentDetails"]["videoId"] for i in data.get("items", [])]

def get_ids_search(channel_id):
    data = safe_get(
        "https://www.googleapis.com/youtube/v3/search",
        {
            "key": YOUTUBE_API_KEY,
            "channelId": channel_id,
            "part": "id",
            "order": "date",
            "maxResults": VIDEO_LIMIT_PER_CHANNEL,
            "type": "video"
        }
    )

    return [i["id"]["videoId"] for i in data.get("items", []) if "videoId" in i.get("id", {})]

def get_videos(ids):
    if not ids:
        return []

    videos = []

    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]

        data = safe_get(
            "https://www.googleapis.com/youtube/v3/videos",
            {"key": YOUTUBE_API_KEY, "id": ",".join(batch), "part": "snippet"}
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

def send(msg):
    try:
        requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            params={"chat_id": CHAT_ID, "text": msg},
            timeout=30
        )
        return True
    except Exception as e:
        print("Ошибка отправки в Telegram:", e)
        return False

def main():
    seen = load_seen()
    print("Уже сохранено видео:", len(seen))

    for url in CHANNEL_URLS:
        print(f"\nПроверяю: {url}")

        cid = get_channel_id(url)
        if not cid:
            print("канал не найден")
            continue

        info = get_channel_info(cid)
        if not info:
            print("нет данных канала")
            continue

        channel_title, playlist = info

        ids = list(dict.fromkeys(get_ids_playlist(playlist) + get_ids_search(cid)))
        videos = sorted(get_videos(ids), key=lambda x: x["date"])

        found = 0

        for v in videos:
            if v["id"] in seen:
                continue

            hits = [k for k in KEYWORDS if k.lower() in v["desc"].lower()]
            if not hits:
                continue

            msg = (
                "Найдена реклама BlancVPN\n\n"
                f"Дата: {format_date(v['date'])}\n"
                f"Канал: {channel_title}\n"
                f"Найдено по: {', '.join(hits)}\n\n"
                f"{v['title']}\n"
                f"https://www.youtube.com/watch?v={v['id']}"
            )

            if send(msg):
                mark_seen(v["id"])
                seen.add(v["id"])
                found += 1
                print("отправлено и сохранено:", v["title"])

        if found == 0:
            print("ничего нового")

if __name__ == "__main__":
    main()
