import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [
    int(admin_id.strip())
    for admin_id in os.getenv("ADMIN_IDS", "").split(",")
    if admin_id.strip()
]

GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    "google_service_account.json",
)

GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if GOOGLE_SERVICE_ACCOUNT_JSON:
    GOOGLE_SERVICE_ACCOUNT_FILE = "/tmp/google_service_account.json"

    with open(GOOGLE_SERVICE_ACCOUNT_FILE, "w", encoding="utf-8") as file:
        file.write(GOOGLE_SERVICE_ACCOUNT_JSON)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не знайдено. Додай його у файл .env")
