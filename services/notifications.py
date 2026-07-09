from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.queries import (
    get_combined_booking_full_info,
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
        f"Статус: очікує підтвердження майстром"
    )

    await bot.send_message(
        chat_id=booking["master_telegram_id"],
        text=text,
        reply_markup=master_confirmation_keyboard(booking_id),
    )

    return True
