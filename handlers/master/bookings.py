from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database.queries import (
    get_booking_full_info,
    get_combined_booking_full_info,
    get_master_by_id,
    update_booking_status,
    update_payment_status,
)

from services.calendar import (
    is_time_free,
    create_calendar_event,
)

router = Router()

SALON_ADDRESS = "Av. 25 de Abril 672, Cascais"


def telegram_user_link_keyboard(telegram_id: int, button_text: str):
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


@router.callback_query(F.data.startswith("master_confirm:"))
async def master_confirm_payment(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])

    booking = await get_combined_booking_full_info(booking_id)

    if not booking:
        await callback.answer("Запис не знайдено", show_alert=True)
        return

    if booking["status"] == "confirmed":
        await callback.answer("Цей запис уже підтверджено ✅", show_alert=True)
        return

    if booking["status"] == "cancelled":
        await callback.answer("Цей запис уже скасовано ❌", show_alert=True)
        return

    services = booking.get("services", [])

    if not services:
        await callback.answer("У записі немає процедур", show_alert=True)
        return

    if booking["client_language"] == "pt":
        service_names = [
            service["name_pt"] if service["name_pt"] else service["name_ua"]
            for service in services
        ]
    else:
        service_names = [service["name_ua"] for service in services]

    services_text = "\n".join(f"• {name}" for name in service_names)

    # ===== Перевірка Google Calendar для кожної процедури =====
    calendar_events_to_create = []

    try:
        for service_item in services:
            master = await get_master_by_id(service_item["master_id"])

            if not master or not master["calendar_id"]:
                continue

            service_name = (
                service_item["name_pt"]
                if booking["client_language"] == "pt" and service_item["name_pt"]
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
                    f"❌ Час для процедури «{service_name}» уже зайнятий у Google Calendar.",
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

        # ===== Створення подій після успішної перевірки =====
        for event_data in calendar_events_to_create:
            event = create_calendar_event(**event_data)
            print("GOOGLE EVENT CREATED:", event.get("id"))

    except Exception as e:
        print(f"Google Calendar error: {e}")
        await callback.answer(
            "❌ Не вдалося створити подію в Google Calendar.",
            show_alert=True,
        )
        return

    await update_booking_status(booking_id, "confirmed")
    await update_payment_status(booking_id, "paid")

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
async def master_reject_booking(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])

    booking = await get_booking_full_info(booking_id)

    if not booking:
        await callback.answer("Запис не знайдено", show_alert=True)
        return

    if booking["status"] == "confirmed":
        await callback.answer("Цей запис уже підтверджено ✅", show_alert=True)
        return

    if booking["status"] == "cancelled":
        await callback.answer("Цей запис уже скасовано ❌", show_alert=True)
        return

    await update_booking_status(booking_id, "cancelled")
    await update_payment_status(booking_id, "cancelled")

    if booking["client_language"] == "pt":
        client_text = (
            "❌ Infelizmente, a marcação não foi confirmada.\n\n"
            "Por favor, contacte a profissional ou tente escolher outro horário."
        )
        button_text = "💬 Contactar profissional"
    else:
        client_text = (
            "❌ На жаль, запис не був підтверджений.\n\n"
            "Будь ласка, зв’яжіться з майстром або спробуйте обрати інший час."
        )
        button_text = "💬 Написати майстру"

    await callback.bot.send_message(
        chat_id=booking["client_telegram_id"],
        text=client_text,
        reply_markup=telegram_user_link_keyboard(
            booking["master_telegram_id"],
            button_text,
        ),
    )

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ Запис відхилено майстром."
    )

    await callback.answer("Клієнту надіслано повідомлення про відхилення ❌")


@router.callback_query(F.data.startswith("master_contact:"))
async def master_contact_client(callback: CallbackQuery):
    booking_id = int(callback.data.split(":")[1])

    booking = await get_booking_full_info(booking_id)

    if not booking:
        await callback.answer("Запис не знайдено", show_alert=True)
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
