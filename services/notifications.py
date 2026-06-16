from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.queries import get_booking_full_info


def master_confirmation_keyboard(booking_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Підтвердити оплату",
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
    booking = await get_booking_full_info(booking_id)

    if not booking:
        return False

    if not booking["master_telegram_id"]:
        return False

    text = (
        "💅 Новий запис очікує підтвердження\n\n"
        f"👤 Клієнт: {booking['client_name']}\n"
        f"📞 Телефон: {booking['client_phone']}\n"
        f"💅 Послуга: {booking['name_ua']}\n"
        f"📅 Дата: {booking['date']}\n"
        f"🕒 Час: {booking['time']}\n"
        f"💳 Завдаток: очікує перевірки"
    )

    await bot.send_message(
        chat_id=booking["master_telegram_id"],
        text=text,
        reply_markup=master_confirmation_keyboard(booking_id),
    )

    return True
