import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")


BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не знайдено. Додай його у файл .env")

if ADMIN_ID:
    ADMIN_ID = int(ADMIN_ID)
