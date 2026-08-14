from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.queries import (
    get_combined_booking_full_info,
    mark_booking_reminder_sent,
)


def master_confirmation_keyboard(booking_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Підтвердити запис",
                    callback_data=f"master_confirm:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Відхилити запис",
                    callback_data=f"master_reject:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Написати клієнту",
                    callback_data=f"master_contact:{booking_id}",
                )
            ],
        ]
    )


async def notify_master_about_booking(bot: Bot, booking_id: int):
    booking = await get_combined_booking_full_info(booking_id)

    if not booking:
        return False

    if not booking["master_telegram_id"]:
        return False

    services_text = ""

    for index, service in enumerate(booking["services"], start=1):
        services_text += (
            f"{index}. {service['name_ua']} — "
            f"{service['price']} €, {service['duration']} хв\n"
        )

        extras = service.get("extras", [])

        if extras:
            for extra in extras:
                services_text += (
                    f"   ➕ {extra.get('name_ua', 'Додатково')} — "
                    f"{extra.get('price', 0)} €, "
                    f"{extra.get('duration', 0)} хв\n"
                )

    text = (
        "💅 Новий запис очікує підтвердження\n\n"
        f"👤 Клієнт: {booking['client_name']}\n"
        f"📞 Телефон: {booking['client_phone']}\n\n"
        f"💅 Процедури:\n{services_text}\n"
        f"📅 Дата: {booking['date']}\n"
        f"🕒 Час: {booking['time']}\n"
        f"⏱ Загальна тривалість: {booking['total_duration']} хв\n"
        f"💰 Загальна сума: {booking['total_price']} €\n\n"
        "Статус: очікує підтвердження майстром"
    )

    await bot.send_message(
        chat_id=booking["master_telegram_id"],
        text=text,
        reply_markup=master_confirmation_keyboard(booking_id),
    )

    return True


def _build_client_services_text(booking: dict, language: str) -> str:
    lines = []

    for service in booking.get("services", []):
        if language == "pt":
            service_name = service.get("name_pt") or service.get("name_ua")
        else:
            service_name = service.get("name_ua") or service.get("name_pt")

        if service_name:
            lines.append(f"• {service_name}")

        for extra in service.get("extras", []):
            if language == "pt":
                extra_name = extra.get("name_pt") or extra.get("name_ua")
            else:
                extra_name = extra.get("name_ua") or extra.get("name_pt")

            if extra_name:
                lines.append(f"  + {extra_name}")

    return "\n".join(lines)


async def send_client_booking_reminder(bot: Bot, booking_id: int) -> bool:
    booking = await get_combined_booking_full_info(booking_id)

    if not booking:
        return False

    client_telegram_id = booking.get("client_telegram_id")

    if not client_telegram_id:
        return False

    language = booking.get("client_language") or "ua"
    services_text = _build_client_services_text(booking, language)

    if language == "pt":
        text = (
            "🌸 Lembrete do seu agendamento na ZoYA Nails Studio\n\n"
            f"💅 Serviços:\n{services_text}\n\n"
            f"👩 Mestre: {booking['master_name']}\n"
            f"📅 Data: {booking['date']}\n"
            f"🕒 Hora: {booking['time']}\n\n"
            "Até breve 🤍"
        )
    else:
        text = (
            "🌸 Нагадуємо про ваш запис у ZoYA Nails Studio завтра\n\n"
            f"💅 Процедури:\n{services_text}\n\n"
            f"👩 Майстер: {booking['master_name']}\n"
            f"📅 Дата: {booking['date']}\n"
            f"🕒 Час: {booking['time']}\n\n"
            "До зустрічі 🤍"
        )

    try:
        await bot.send_message(
            chat_id=client_telegram_id,
            text=text,
        )
    except Exception:
        return False

    await mark_booking_reminder_sent(booking_id)
    return True
