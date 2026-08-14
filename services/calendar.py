from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import GOOGLE_SERVICE_ACCOUNT_FILE

SCOPES = ["https://www.googleapis.com/auth/calendar"]
DEFAULT_TIMEZONE = "Europe/Lisbon"


def get_calendar_service():
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )

    return build(
        "calendar",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )


def build_datetime(
    date: str,
    time: str,
    timezone: str = DEFAULT_TIMEZONE,
):
    naive_dt = datetime.strptime(
        f"{date} {time}",
        "%Y-%m-%d %H:%M",
    )
    return naive_dt.replace(
        tzinfo=ZoneInfo(timezone),
    )


def get_busy_intervals(
    calendar_id: str,
    date: str,
    start_time: str,
    end_time: str,
    timezone: str = DEFAULT_TIMEZONE,
):
    """
    Отримує всі зайняті інтервали календаря одним запитом
    за вказаний робочий проміжок дня.
    """
    if not calendar_id:
        return []

    service = get_calendar_service()

    start_dt = build_datetime(
        date,
        start_time,
        timezone,
    )
    end_dt = build_datetime(
        date,
        end_time,
        timezone,
    )

    body = {
        "timeMin": start_dt.isoformat(),
        "timeMax": end_dt.isoformat(),
        "timeZone": timezone,
        "items": [{"id": calendar_id}],
    }

    result = service.freebusy().query(body=body).execute()

    busy_items = result.get("calendars", {}).get(calendar_id, {}).get("busy", [])

    intervals = []

    for item in busy_items:
        busy_start = datetime.fromisoformat(item["start"].replace("Z", "+00:00"))
        busy_end = datetime.fromisoformat(item["end"].replace("Z", "+00:00"))

        intervals.append(
            (
                busy_start.astimezone(ZoneInfo(timezone)),
                busy_end.astimezone(ZoneInfo(timezone)),
            )
        )

    return intervals


def slot_overlaps_busy(
    date: str,
    time: str,
    duration: int,
    busy_intervals,
    timezone: str = DEFAULT_TIMEZONE,
):
    """
    Перевіряє слот локально, без нового запиту до Google.
    """
    slot_start = build_datetime(
        date,
        time,
        timezone,
    )
    slot_end = slot_start + timedelta(
        minutes=duration,
    )

    for busy_start, busy_end in busy_intervals:
        if slot_start < busy_end and slot_end > busy_start:
            return True

    return False


def is_time_free(
    calendar_id: str,
    date: str,
    time: str,
    duration: int,
    timezone: str = DEFAULT_TIMEZONE,
):
    """
    Залишено для сумісності зі старим кодом.
    Для масової перевірки слотів краще використовувати
    get_busy_intervals() + slot_overlaps_busy().
    """
    start_dt = build_datetime(
        date,
        time,
        timezone,
    )
    end_dt = start_dt + timedelta(
        minutes=duration,
    )

    busy_intervals = get_busy_intervals(
        calendar_id=calendar_id,
        date=date,
        start_time=start_dt.strftime("%H:%M"),
        end_time=end_dt.strftime("%H:%M"),
        timezone=timezone,
    )

    return not slot_overlaps_busy(
        date=date,
        time=time,
        duration=duration,
        busy_intervals=busy_intervals,
        timezone=timezone,
    )


def create_calendar_event(
    calendar_id: str,
    client_name: str,
    client_phone: str,
    service_name: str,
    master_name: str,
    date: str,
    time: str,
    duration: int,
    timezone: str = DEFAULT_TIMEZONE,
):
    service = get_calendar_service()

    start_dt = build_datetime(
        date,
        time,
        timezone,
    )
    end_dt = start_dt + timedelta(
        minutes=duration,
    )

    event = {
        "summary": (f"{service_name} — {client_name}"),
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


def update_calendar_event(
    calendar_id: str,
    event_id: str,
    date: str,
    time: str,
    duration: int,
    timezone: str = DEFAULT_TIMEZONE,
):
    if not calendar_id or not event_id:
        return None

    service = get_calendar_service()

    event = (
        service.events()
        .get(
            calendarId=calendar_id,
            eventId=event_id,
        )
        .execute()
    )

    start_dt = build_datetime(
        date,
        time,
        timezone,
    )
    end_dt = start_dt + timedelta(
        minutes=duration,
    )

    event["start"] = {
        "dateTime": start_dt.isoformat(),
        "timeZone": timezone,
    }

    event["end"] = {
        "dateTime": end_dt.isoformat(),
        "timeZone": timezone,
    }

    updated_event = (
        service.events()
        .update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event,
        )
        .execute()
    )

    return updated_event


def delete_calendar_event(
    calendar_id: str,
    event_id: str,
):
    if not calendar_id or not event_id:
        return False

    service = get_calendar_service()

    try:
        (
            service.events()
            .delete(
                calendarId=calendar_id,
                eventId=event_id,
            )
            .execute()
        )
        return True
    except Exception:
        return False
