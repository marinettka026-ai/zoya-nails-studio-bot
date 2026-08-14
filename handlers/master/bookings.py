import json

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from database.queries import (
    delete_booking_by_id,
    get_combined_booking_full_info,
    get_master_by_id,
    update_booking_calendar_events,
    update_booking_status,
    update_payment_status,
)

from services.calendar import (
    create_calendar_event,
    delete_calendar_event,
    is_time_free,
)

router = Router()

SALON_ADDRESS = "Av. 25 de Abril 672, Cascais"


def telegram_user_link_keyboard(
    telegram_id: int,
    button_text: str,
):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=button_text,
                    url=f"tg://user?id={telegram_id}",
                )
            ]
        ]
    )


def parse_calendar_events(raw_value):
    if not raw_value:
        return []

    if isinstance(raw_value, list):
        return raw_value

    try:
        parsed = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return []

    return parsed if isinstance(parsed, list) else []


async def delete_google_events(raw_value):
    events = parse_calendar_events(raw_value)

    for event in events:
        calendar_id = event.get("calendar_id")
        event_id = event.get("event_id")

        if not calendar_id or not event_id:
            continue

        try:
            delete_calendar_event(
                calendar_id=calendar_id,
                event_id=event_id,
            )
        except Exception as error:
            print(
                "GOOGLE CALENDAR DELETE ERROR:",
                calendar_id,
                event_id,
                repr(error),
            )


@router.callback_query(F.data.startswith("master_confirm:"))
async def master_confirm_payment(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])

    booking = await get_combined_booking_full_info(
        booking_id,
    )

    if not booking:
        await callback.answer(
            "Запис не знайдено",
            show_alert=True,
        )
        return

    if booking["status"] == "confirmed":
        await callback.answer(
            "Цей запис уже підтверджено ✅",
            show_alert=True,
        )
        return

    services = booking.get("services", [])

    if not services:
        await callback.answer(
            "У записі немає процедур",
            show_alert=True,
        )
        return

    if booking["client_language"] == "pt":
        service_names = [
            (service["name_pt"] if service["name_pt"] else service["name_ua"])
            for service in services
        ]
    else:
        service_names = [service["name_ua"] for service in services]

    services_text = "\n".join(f"• {name}" for name in service_names)

    calendar_events_to_create = []

    try:
        for service_item in services:
            master = await get_master_by_id(
                service_item["master_id"],
            )

            if not master or not master["calendar_id"]:
                continue

            service_name = (
                service_item["name_pt"]
                if (booking["client_language"] == "pt" and service_item["name_pt"])
                else service_item["name_ua"]
            )

            event_date = service_item["date"] or booking["date"]
            event_time = service_item["start_time"] or booking["time"]
            event_duration = service_item["duration"] or booking["total_duration"]

            is_free = is_time_free(
                calendar_id=master["calendar_id"],
                date=event_date,
                time=event_time,
                duration=event_duration,
            )

            if not is_free:
                await callback.answer(
                    (
                        f"❌ Час для процедури "
                        f"«{service_name}» уже зайнятий "
                        f"у Google Calendar."
                    ),
                    show_alert=True,
                )
                return

            calendar_events_to_create.append(
                {
                    "calendar_id": master["calendar_id"],
                    "client_name": booking["client_name"],
                    "client_phone": booking["client_phone"],
                    "service_name": service_name,
                    "master_name": master["name"],
                    "date": event_date,
                    "time": event_time,
                    "duration": event_duration,
                }
            )

    except Exception as error:
        print(
            "GOOGLE CALENDAR CHECK ERROR:",
            repr(error),
        )
        await callback.answer(
            "❌ Не вдалося перевірити Google Calendar.",
            show_alert=True,
        )
        return

    created_calendar_events = []

    try:
        for event_data in calendar_events_to_create:
            event = create_calendar_event(
                **event_data,
            )

            event_id = event.get("id")

            if event_id:
                created_calendar_events.append(
                    {
                        "calendar_id": event_data["calendar_id"],
                        "event_id": event_id,
                    }
                )

                print(
                    "GOOGLE EVENT CREATED:",
                    event_id,
                )

    except Exception as error:
        print(
            "GOOGLE CALENDAR CREATE ERROR:",
            repr(error),
        )

        for created_event in created_calendar_events:
            try:
                delete_calendar_event(
                    calendar_id=created_event["calendar_id"],
                    event_id=created_event["event_id"],
                )
            except Exception:
                pass

        await callback.answer(
            "❌ Не вдалося створити подію в Google Calendar.",
            show_alert=True,
        )
        return

    await update_booking_calendar_events(
        booking_id=booking_id,
        calendar_events=created_calendar_events,
    )

    await update_booking_status(
        booking_id,
        "confirmed",
    )
    await update_payment_status(
        booking_id,
        "paid",
    )

    if booking["client_language"] == "pt":
        client_text = (
            "✅ A sua marcação foi confirmada!\n\n"
            f"Profissional: {booking['master_name']}\n"
            f"Serviços:\n{services_text}\n"
            f"Data: {booking['date']}\n"
            f"Hora: {booking['time']}\n"
            f"Morada: {SALON_ADDRESS}\n\n"
            "Até breve no ZoYA Nails Studio 🌸"
        )
    else:
        client_text = (
            "✅ Ваш запис підтверджено!\n\n"
            f"Майстер: {booking['master_name']}\n"
            f"Процедури:\n{services_text}\n"
            f"Дата: {booking['date']}\n"
            f"Час: {booking['time']}\n"
            f"Адреса: {SALON_ADDRESS}\n\n"
            "До зустрічі у ZoYA Nails Studio 🌸"
        )

    await callback.bot.send_message(
        chat_id=booking["client_telegram_id"],
        text=client_text,
    )

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ Запис підтверджено майстром."
    )

    await callback.answer("Клієнту надіслано підтвердження ✅")


@router.callback_query(F.data.startswith("master_reject:"))
async def master_reject_booking(
    callback: CallbackQuery,
):
    booking_id = int(callback.data.split(":")[1])

    booking = await get_combined_booking_full_info(
        booking_id,
    )

    if not booking:
        await callback.answer(
            "Запис не знайдено",
            show_alert=True,
        )
        return

    # Спочатку прибираємо всі події з Google Calendar.
    await delete_google_events(
        booking.get("calendar_event_id"),
    )

    # Потім повністю видаляємо запис із БД.
    deleted = await delete_booking_by_id(
        booking_id,
    )

    if not deleted:
        await callback.answer(
            "❌ Не вдалося видалити запис із бази.",
            show_alert=True,
        )
        return

    if booking["client_language"] == "pt":
        client_text = (
            "❌ A sua marcação foi cancelada pela profissional.\n\n"
            f"Profissional: {booking['master_name']}\n"
            f"Data: {booking['date']}\n"
            f"Hora: {booking['time']}\n\n"
            "Pode escolher outra data e hora no bot."
        )
        button_text = "💬 Contactar profissional"
    else:
        client_text = (
            "❌ Майстер скасував ваш запис.\n\n"
            f"Майстер: {booking['master_name']}\n"
            f"Дата: {booking['date']}\n"
            f"Час: {booking['time']}\n\n"
            "Ви можете обрати іншу дату та час у боті."
        )
        button_text = "💬 Написати майстру"

    try:
        await callback.bot.send_message(
            chat_id=booking["client_telegram_id"],
            text=client_text,
            reply_markup=telegram_user_link_keyboard(
                booking["master_telegram_id"],
                button_text,
            ),
        )
    except Exception as error:
        print(
            "CLIENT CANCEL NOTIFICATION ERROR:",
            repr(error),
        )

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ Запис скасовано майстром."
    )

    await callback.answer("Запис видалено з бази та календаря ❌")


@router.callback_query(F.data.startswith("master_contact:"))
async def master_contact_client(
    callback: CallbackQuery,
):
    booking_id = int(callback.data.split(":")[1])

    booking = await get_combined_booking_full_info(
        booking_id,
    )

    if not booking:
        await callback.answer(
            "Запис не знайдено",
            show_alert=True,
        )
        return

    await callback.message.answer(
        "💬 Дані для зв’язку з клієнтом:\n\n"
        f"👤 Ім’я: {booking['client_name']}\n"
        f"📞 Телефон: {booking['client_phone']}",
        reply_markup=telegram_user_link_keyboard(
            booking["client_telegram_id"],
            "💬 Відкрити чат з клієнтом",
        ),
    )

    await callback.answer()
