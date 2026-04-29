import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

KEYWORDS = ["BlancVPN", "https://blanc.link/"]

VIDEO_LIMIT_API = 200
SEEN_FILE = "seen_videos.txt"

CHANNELS = [
    {"name": "Max Katz", "id": "UCUGfDbfRIx51kJGGHIFo8Rw"},
    {"name": "vdud", "id": "UCMCgOm8GZkHp8zJ6l7_hIuA"},
    {"name": "Kolezev", "id": "UCLxr1ACVGlrUvpGkc_ruMKg"},
    {"name": "Web3nity", "id": "UCuaYG7fdQ-4myL_CVtvwNHQ"},
    {"name": "Ruslan Belyy", "id": "UC71duAY6rjGEhGQAiytiFPw"},
    {"name": "VadimKey", "id": "UCUS6gJ_FCzLS5w2InH6oYmA"},
    {"name": "Gordeeva", "id": "UCpJuziZAwEFnoeNGSaxQlCQ"},
    {"name": "Zhukova", "id": "UC30guDBHUu_3j-uZdlfo9TQ"},
    {"name": "Spoontamer", "id": "UCR-Hcwi27-Ee6VnGzmxE1pA"},
    {"name": "MackNack", "id": "UCgpSieplNxXxLXYAzJLLpng"},
    {"name": "Varlamov", "id": "UC101o-vQ2iOj9vr00JUlyKw"},
    {"name": "Ekaterina Schulmann", "id": "UCL1rJ0ROIw9V1qFeIN0ZTZQ"},
    {"name": "Radio Dolin", "id": "UCe5_WsZ_7RM14t3MImLWNZg"},
    {"name": "Vraevskiy", "id": "UCZy0mCOt6izb2o1bQEUNGRg"},
    {"name": "Alex Shevtsov", "id": "UCM7-8EfoIv0T9cCI4FhHbKQ"}
]

def load_seen():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        for video_id in sorted(seen):
            f.write(video_id + "\n")

def safe_get_json(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=30)
        data = r.json()
        if "error" in data:
            print("API error:", data["error"].get("message", data["error"]))
            return {}
        return data
    except Exception as e:
        print("Request error:", e)
        return {}

def get_ids_from_rss(channel_id):
    ids = []
    try:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        r = requests.get(url, timeout=30)
        root = ET.fromstring(r.text)

        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            video_id = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId")
            if video_id is not None:
                ids.append(video_id.text)
    except Exception as e:
        print("RSS error:", e)

    return ids

def get_ids_from_api(channel_id):
    ids = []
    next_page = None

    while len(ids) < VIDEO_LIMIT_API:
        params = {
            "key": YOUTUBE_API_KEY,
            "channelId": channel_id,
            "part": "id",
            "order": "date",
            "maxResults": 50,
            "type": "video"
        }

        if next_page:
            params["pageToken"] = next_page

        data = safe_get_json("https://www.googleapis.com/youtube/v3/search", params)

        for item in data.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if video_id:
                ids.append(video_id)

        next_page = data.get("nextPageToken")
        if not next_page:
            break

    return ids[:VIDEO_LIMIT_API]

def get_video_details(video_ids):
    videos = []

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]

        data = safe_get_json(
            "https://www.googleapis.com/youtube/v3/videos",
            {
                "key": YOUTUBE_API_KEY,
                "id": ",".join(batch),
                "part": "snippet"
            }
        )

        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            videos.append({
                "id": item["id"],
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt", "")
            })

    return videos

def format_date(date_str):
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y")
    except:
        return "не указана"

def has_keywords(description):
    text = description.lower()
    return [k for k in KEYWORDS if k.lower() in text]

def send_telegram(message):
    try:
        requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            params={"chat_id": CHAT_ID, "text": message},
            timeout=30
        )
        return True
    except Exception as e:
        print("Telegram error:", e)
        return False

def main():
    if not YOUTUBE_API_KEY:
        print("Нет YOUTUBE_API_KEY")
        return

    if not TELEGRAM_TOKEN:
        print("Нет TELEGRAM_TOKEN")
        return

    if not CHAT_ID:
        print("Нет CHAT_ID")
        return

    seen = load_seen()
    first_run = len(seen) == 0

    print(f"Уже сохранено рекламных видео: {len(seen)}")

    newly_seen = set(seen)

    for channel in CHANNELS:
        print(f"\nКанал: {channel['name']}")

        ids = []
        ids.extend(get_ids_from_rss(channel["id"]))
        ids.extend(get_ids_from_api(channel["id"]))

        ids = list(dict.fromkeys(ids))

        print(f"Видео собрано: {len(ids)}")

        videos = get_video_details(ids)

        for video in videos:
            video_id = video["id"]

            if video_id in seen:
                continue

            found_keywords = has_keywords(video["description"])

            if not found_keywords:
                continue

            newly_seen.add(video_id)

            if first_run:
                print(f"База создана без отправки: {video['title']}")
                continue

            message = (
                "Найдена реклама BlancVPN\n\n"
                f"Дата: {format_date(video['published_at'])}\n"
                f"Канал: {channel['name']}\n"
                f"Найдено по: {', '.join(found_keywords)}\n\n"
                f"{video['title']}\n"
                f"https://www.youtube.com/watch?v={video_id}"
            )

            if send_telegram(message):
                print(f"Отправлено: {video['title']}")

    save_seen(newly_seen)

    if first_run:
        print("\nПервый запуск: база старых рекламных видео создана. Старые ролики не отправлялись.")
    else:
        print("\nПроверка завершена.")

if __name__ == "__main__":
    main()
