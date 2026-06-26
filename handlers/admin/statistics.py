from aiogram import Router, F
from aiogram.types import Message

from config import ADMIN_IDS
from database.queries import get_all_users, get_all_bookings
from locales.ua import BUTTONS as UA_BUTTONS

router = Router()


@router.message(F.text == UA_BUTTONS["admin_statistics"])
async def admin_statistics(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас немає доступу.")
        return

    users = await get_all_users()
    bookings = await get_all_bookings()

    await message.answer(
        "📊 Статистика\n\n"
        f"👥 Клієнтів: {len(users)}\n"
        f"📅 Записів: {len(bookings)}"
    )
