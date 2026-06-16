from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import ADMIN_ID

from database.queries import (
    get_all_bookings,
    get_future_bookings,
    get_past_bookings,
    update_booking_status,
    delete_all_bookings,
)
from keyboards.menus import admin_menu
from locales.ua import BUTTONS as UA_BUTTONS

router = Router()


def row_get(row, key, default="Не вказано"):
    try:
        value = row[key]
        return value if value is not None else default
    except (KeyError, IndexError):
        return default


def admin_bookings_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Майбутні записи",
                    callback_data="admin_bookings_future",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🕓 Минулі записи",
                    callback_data="admin_bookings_past",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Всі записи",
                    callback_data="admin_bookings_all",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="admin_bookings_back",
                )
            ],
        ]
    )


def bookings_keyboard(bookings):
    keyboard = []

    for booking in bookings:
        booking_id = row_get(booking, "id")
        client_name = row_get(booking, "client_name", "Клієнт")
        date_time = row_get(booking, "datetime", "Дата не вказана")

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"📅 {date_time} | {client_name}",
                    callback_data=f"admin_booking:{booking_id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад до записів",
                callback_data="admin_bookings_menu",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def booking_details_keyboard(booking_id: int, phone: str = None):
    keyboard = []

    if phone and phone != "Не вказано":
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="📞 Зв'язок з клієнтом",
                    url=f"https://t.me/+{clean_phone}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="❌ Скасувати запис",
                callback_data=f"admin_cancel_booking_confirm:{booking_id}",
            )
        ]
    )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад до записів",
                callback_data="admin_bookings_menu",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(F.text == UA_BUTTONS["admin_bookings"])
async def admin_bookings(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас немає доступу.")
        return

    await message.answer(
        "📋 Записи\n\n" "Оберіть, які записи показати:",
        reply_markup=admin_bookings_menu_keyboard(),
    )


@router.callback_query(F.data == "admin_bookings_menu")
async def admin_bookings_menu(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    await callback.message.answer(
        "📋 Записи\n\n" "Оберіть, які записи показати:",
        reply_markup=admin_bookings_menu_keyboard(),
    )

    await callback.answer()


@router.callback_query(F.data == "admin_bookings_future")
async def show_future_bookings(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    bookings = await get_future_bookings()

    if not bookings:
        await callback.message.answer(
            "📅 Майбутні записи\n\n" "Майбутніх записів поки немає.",
            reply_markup=admin_bookings_menu_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.answer(
        "📅 Майбутні записи\n\n" "Оберіть запис, щоб переглянути деталі:",
        reply_markup=bookings_keyboard(bookings),
    )

    await callback.answer()


@router.callback_query(F.data == "admin_bookings_past")
async def show_past_bookings(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    bookings = await get_past_bookings()

    if not bookings:
        await callback.message.answer(
            "🕓 Минулі записи\n\n" "Минулих записів поки немає.",
            reply_markup=admin_bookings_menu_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.answer(
        "🕓 Минулі записи\n\n" "Оберіть запис, щоб переглянути деталі:",
        reply_markup=bookings_keyboard(bookings),
    )

    await callback.answer()


@router.callback_query(F.data == "admin_bookings_all")
async def show_all_bookings(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    bookings = await get_all_bookings()

    if not bookings:
        await callback.message.answer(
            "📋 Всі записи\n\n" "Записів поки немає.",
            reply_markup=admin_bookings_menu_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.answer(
        "📋 Всі записи\n\n" "Оберіть запис, щоб переглянути деталі:",
        reply_markup=bookings_keyboard(bookings),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("admin_booking:"))
async def admin_booking_details(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    booking_id = int(callback.data.split(":")[1])
    bookings = await get_all_bookings()

    booking = None

    for item in bookings:
        if row_get(item, "id") == booking_id:
            booking = item
            break

    if not booking:
        await callback.answer("Запис не знайдено", show_alert=True)
        return

    text = (
        "📋 Деталі запису\n\n"
        f"🆔 ID: {row_get(booking, 'id')}\n"
        f"👤 Клієнт: {row_get(booking, 'client_name')}\n"
        f"📞 Телефон: {row_get(booking, 'phone')}\n"
        f"👩 Майстер: {row_get(booking, 'master_name')}\n"
        f"💅 Послуга: {row_get(booking, 'service_name')}\n"
        f"📅 Дата: {row_get(booking, 'date')}\n"
        f"🕒 Час: {row_get(booking, 'time')}\n"
        f"💶 Оплата: {row_get(booking, 'payment_status')}\n"
        f"📌 Статус: {row_get(booking, 'status')}\n"
    )

    await callback.message.answer(
        text,
        reply_markup=booking_details_keyboard(
            booking_id,
            row_get(booking, "phone"),
        ),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("admin_cancel_booking_confirm:"))
async def admin_cancel_booking_confirm(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    booking_id = int(callback.data.split(":")[1])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Так, скасувати",
                    callback_data=f"admin_cancel_booking:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Ні, назад",
                    callback_data=f"admin_booking:{booking_id}",
                )
            ],
        ]
    )

    await callback.message.answer(
        "⚠️ Ви точно хочете скасувати цей запис?",
        reply_markup=keyboard,
    )

    await callback.answer()


@router.callback_query(F.data.startswith("admin_cancel_booking:"))
async def admin_cancel_booking(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    booking_id = int(callback.data.split(":")[1])

    await update_booking_status(booking_id, "cancelled")

    await callback.message.answer(
        "❌ Запис скасовано.\n\n"
        "Він залишиться в історії, але матиме статус: cancelled.\n"
        "Час стане доступним для нового запису.",
        reply_markup=admin_bookings_menu_keyboard(),
    )

    await callback.answer()


@router.callback_query(F.data == "admin_bookings_back")
async def admin_bookings_back(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    await callback.message.answer(
        "Адмін-панель:",
        reply_markup=admin_menu(),
    )

    await callback.answer()


@router.message(F.text == "/clear_bookings")
async def clear_bookings(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    await delete_all_bookings()

    await message.answer("🗑 Усі записи видалені.")
