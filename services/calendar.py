from datetime import datetime, time, timedelta
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


def _parse_google_event_datetime(
    event_part: dict,
    timezone: str,
):
    tz = ZoneInfo(timezone)

    date_time_value = event_part.get("dateTime")

    if date_time_value:
        parsed = datetime.fromisoformat(date_time_value.replace("Z", "+00:00"))
        return parsed.astimezone(tz)

    date_value = event_part.get("date")

    if date_value:
        parsed_date = datetime.strptime(
            date_value,
            "%Y-%m-%d",
        ).date()

        return datetime.combine(
            parsed_date,
            time.min,
            tzinfo=tz,
        )

    return None


def get_busy_intervals(
    calendar_id: str,
    date: str,
    start_time: str,
    end_time: str,
    timezone: str = DEFAULT_TIMEZONE,
):
    """
    Отримує реальні події Google Calendar за потрібний проміжок.

    Будь-яка подія в календарі вважається зайнятим часом,
    навіть якщо в Google Calendar вона позначена як Free.
    """
    if not calendar_id:
        return []

    service = get_calendar_service()

    range_start = build_datetime(
        date,
        start_time,
        timezone,
    )
    range_end = build_datetime(
        date,
        end_time,
        timezone,
    )

    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=range_start.isoformat(),
            timeMax=range_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            showDeleted=False,
            maxResults=2500,
        )
        .execute()
    )

    intervals = []

    for event in result.get("items", []):
        if event.get("status") == "cancelled":
            continue

        event_start = _parse_google_event_datetime(
            event.get("start", {}),
            timezone,
        )
        event_end = _parse_google_event_datetime(
            event.get("end", {}),
            timezone,
        )

        if not event_start or not event_end:
            continue

        if event_start < range_end and event_end > range_start:
            intervals.append(
                (
                    event_start,
                    event_end,
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
    slot_start = build_datetime(
        date,
        time,
        timezone,
    )
    slot_end = slot_start + timedelta(
        minutes=duration,
    )

    busy_intervals = get_busy_intervals(
        calendar_id=calendar_id,
        date=date,
        start_time=slot_start.strftime("%H:%M"),
        end_time=slot_end.strftime("%H:%M"),
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

    except Exception as error:
        print(
            "GOOGLE CALENDAR DELETE ERROR:",
            calendar_id,
            event_id,
            repr(error),
        )
        return False
