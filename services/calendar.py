from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import GOOGLE_SERVICE_ACCOUNT_FILE

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )

    return build("calendar", "v3", credentials=credentials)


def build_datetime(date: str, time: str, timezone: str = "Europe/Lisbon"):
    naive_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    return naive_dt.replace(tzinfo=ZoneInfo(timezone))


def is_time_free(
    calendar_id: str,
    date: str,
    time: str,
    duration: int,
    timezone: str = "Europe/Lisbon",
):
    service = get_calendar_service()

    start_dt = build_datetime(date, time, timezone)
    end_dt = start_dt + timedelta(minutes=duration)

    body = {
        "timeMin": start_dt.isoformat(),
        "timeMax": end_dt.isoformat(),
        "timeZone": timezone,
        "items": [{"id": calendar_id}],
    }

    result = service.freebusy().query(body=body).execute()
    busy_times = result["calendars"][calendar_id]["busy"]

    return len(busy_times) == 0


def create_calendar_event(
    calendar_id: str,
    client_name: str,
    client_phone: str,
    service_name: str,
    master_name: str,
    date: str,
    time: str,
    duration: int,
    timezone: str = "Europe/Lisbon",
):
    service = get_calendar_service()

    start_dt = build_datetime(date, time, timezone)
    end_dt = start_dt + timedelta(minutes=duration)

    event = {
        "summary": f"{service_name} — {client_name}",
        "description": (
            f"Клієнт: {client_name}\n"
            f"Телефон: {client_phone}\n"
            f"Майстер: {master_name}\n"
            f"Послуга: {service_name}"
        ),
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": timezone,
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": timezone,
        },
    }

    created_event = (
        service.events()
        .insert(
            calendarId=calendar_id,
            body=event,
        )
        .execute()
    )

    return created_event
