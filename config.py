import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [
    int(admin_id.strip())
    for admin_id in os.getenv("ADMIN_IDS", "").split(",")
    if admin_id.strip()
]

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не знайдено. Додай його у файл .env")
