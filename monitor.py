import os
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

requests.get(
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
    params={
        "chat_id": CHAT_ID,
        "text": "Тест: GitHub Actions отправляет сообщения в Telegram"
    }
)
