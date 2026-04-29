import requests
from datetime import datetime

YOUTUBE_API_KEY = "AIzaSyBEQXQN8IRngxmluniVomypIom3yfGPIVg"
TELEGRAM_TOKEN = "8212896282:AAHllkETjlCa94yu-MDukQlh5iHp-LiuzXg"
CHAT_ID = "-1003992190647"

KEYWORDS = ["BlancVPN", "https://blanc.link/"]
VIDEO_LIMIT_PER_CHANNEL = 30
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

def mark_seen(video_id):
    with open(SEEN_FILE, "a", encoding="utf-8") as f:
        f.write(video_id + "\n")

def safe_get(url, params=None):
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if "error" in data:
            print("YouTube API error:", data["error"].get("message", data["error"]))
            return {}

        return data
    except Exception as e:
        print("Ошибка запроса:", e)
        return {}

def format_date(youtube_date):
    try:
        dt = datetime.fromisoformat(youtube_date.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y")
    except:
        return "не указана"

def get_channel_info(channel_id):
    data = safe_get(
        "https://www.googleapis.com/youtube/v3/channels",
        {
            "key": YOUTUBE_API_KEY,
            "id": channel_id,
            "part": "snippet,contentDetails"
        }
    )

    items = data.get("items", [])
    if not items:
        return None

    item = items[0]
    return {
        "title": item["snippet"]["title"],
        "uploads_playlist_id": item["contentDetails"]["relatedPlaylists"]["uploads"]
    }

def get_ids_from_uploads_playlist(playlist_id):
    data = safe_get(
        "https://www.googleapis.com/youtube/v3/playlistItems",
        {
            "key": YOUTUBE_API_KEY,
            "playlistId": playlist_id,
            "part": "contentDetails",
            "maxResults": VIDEO_LIMIT_PER_CHANNEL
        }
    )

    ids = []
    for item in data.get("items", []):
        video_id = item.get("contentDetails", {}).get("videoId")
        if video_id:
            ids.append(video_id)

    return ids

def get_ids_from_channel_search(channel_id):
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

    ids = []
    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        if video_id:
            ids.append(video_id)

    return ids

def get_video_details(video_ids):
    if not video_ids:
        return []

    videos = []

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]

        data = safe_get(
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

def send_telegram(message):
    try:
        requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            params={"chat_id": CHAT_ID, "text": message},
            timeout=30
        )
        return True
    except Exception as e:
        print("Ошибка отправки в Telegram:", e)
        return False

def main():
    seen = load_seen()
    print(f"Уже сохранено видео: {len(seen)}")

    for channel in CHANNELS:
        channel_name = channel["name"]
        channel_id = channel["id"]

        print(f"\nПроверяю: {channel_name}")

        channel_info = get_channel_info(channel_id)
        if not channel_info:
            print("нет данных канала")
            continue

        channel_title = channel_info["title"]
        playlist_id = channel_info["uploads_playlist_id"]

        ids_from_playlist = get_ids_from_uploads_playlist(playlist_id)
        ids_from_search = get_ids_from_channel_search(channel_id)

        all_ids = list(dict.fromkeys(ids_from_playlist + ids_from_search))
        print(f"Видео собрано для проверки: {len(all_ids)}")

        videos = get_video_details(all_ids)
        videos = sorted(videos, key=lambda x: x["published_at"])

        found = 0

        for video in videos:
            video_id = video["id"]

            if video_id in seen:
                continue

            description = video["description"]

            found_keywords = [
                keyword for keyword in KEYWORDS
                if keyword.lower() in description.lower()
            ]

            if not found_keywords:
                continue

            published_date = format_date(video["published_at"])
            link = f"https://www.youtube.com/watch?v={video_id}"

            message = (
                "Найдена реклама BlancVPN\n\n"
                f"Дата: {published_date}\n"
                f"Канал: {channel_title}\n"
                f"Найдено по: {', '.join(found_keywords)}\n\n"
                f"{video['title']}\n"
                f"{link}"
            )

            if send_telegram(message):
                mark_seen(video_id)
                seen.add(video_id)
                found += 1
                print(f"отправлено: {video['title']}")

        if found == 0:
            print("ничего нового")

if __name__ == "__main__":
    main()
