import json

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import ADMIN_IDS
from database.queries import (
    delete_all_bookings,
    delete_booking_by_id,
    get_all_bookings,
    get_combined_booking_full_info,
    get_future_bookings,
    get_past_bookings,
)
from keyboards.menus import admin_menu
from locales.ua import BUTTONS as UA_BUTTONS
from services.calendar import delete_calendar_event

router = Router()


def row_get(row, key, default="Не вказано"):
    try:
        value = row[key]
        return value if value is not None else default
    except (KeyError, IndexError):
        return default


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
                "ADMIN GOOGLE CALENDAR DELETE ERROR:",
                calendar_id,
                event_id,
                repr(error),
            )


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
        client_name = row_get(
            booking,
            "client_name",
            "Клієнт",
        )
        date_time = row_get(
            booking,
            "datetime",
            "Дата не вказана",
        )

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

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard,
    )


def booking_details_keyboard(
    booking_id: int,
    phone: str = None,
):
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
                callback_data=(f"admin_cancel_booking_confirm:" f"{booking_id}"),
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

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard,
    )


@router.message(F.text == UA_BUTTONS["admin_bookings"])
async def admin_bookings(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас немає доступу.")
        return

    await message.answer(
        "📋 Записи\n\n" "Оберіть, які записи показати:",
        reply_markup=admin_bookings_menu_keyboard(),
    )


@router.callback_query(F.data == "admin_bookings_menu")
async def admin_bookings_menu(
    callback: CallbackQuery,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "⛔ Немає доступу",
            show_alert=True,
        )
        return

    await callback.message.answer(
        "📋 Записи\n\n" "Оберіть, які записи показати:",
        reply_markup=admin_bookings_menu_keyboard(),
    )

    await callback.answer()


@router.callback_query(F.data == "admin_bookings_future")
async def show_future_bookings(
    callback: CallbackQuery,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "⛔ Немає доступу",
            show_alert=True,
        )
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
async def show_past_bookings(
    callback: CallbackQuery,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "⛔ Немає доступу",
            show_alert=True,
        )
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
async def show_all_bookings(
    callback: CallbackQuery,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "⛔ Немає доступу",
            show_alert=True,
        )
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
async def admin_booking_details(
    callback: CallbackQuery,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "⛔ Немає доступу",
            show_alert=True,
        )
        return

    booking_id = int(callback.data.split(":")[1])
    bookings = await get_all_bookings()

    booking = None

    for item in bookings:
        if row_get(item, "id") == booking_id:
            booking = item
            break

    if not booking:
        await callback.answer(
            "Запис не знайдено",
            show_alert=True,
        )
        return

    text = (
        "📋 Деталі запису\n\n"
        f"🆔 ID: {row_get(booking, 'id')}\n"
        f"👤 Клієнт: "
        f"{row_get(booking, 'client_name')}\n"
        f"📞 Телефон: "
        f"{row_get(booking, 'phone')}\n"
        f"👩 Майстер: "
        f"{row_get(booking, 'master_name')}\n"
        f"💅 Послуга: "
        f"{row_get(booking, 'service_name')}\n"
        f"📅 Дата: "
        f"{row_get(booking, 'date')}\n"
        f"🕒 Час: "
        f"{row_get(booking, 'time')}\n"
        f"💶 Оплата: "
        f"{row_get(booking, 'payment_status')}\n"
        f"📌 Статус: "
        f"{row_get(booking, 'status')}\n"
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
async def admin_cancel_booking_confirm(
    callback: CallbackQuery,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "⛔ Немає доступу",
            show_alert=True,
        )
        return

    booking_id = int(callback.data.split(":")[1])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Так, скасувати",
                    callback_data=(f"admin_cancel_booking:" f"{booking_id}"),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Ні, назад",
                    callback_data=(f"admin_booking:" f"{booking_id}"),
                )
            ],
        ]
    )

    await callback.message.answer(
        "⚠️ Ви точно хочете скасувати " "цей запис?",
        reply_markup=keyboard,
    )

    await callback.answer()


@router.callback_query(F.data.startswith("admin_cancel_booking:"))
async def admin_cancel_booking(
    callback: CallbackQuery,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "⛔ Немає доступу",
            show_alert=True,
        )
        return

    booking_id = int(callback.data.split(":")[1])

    booking = await get_combined_booking_full_info(booking_id)

    if not booking:
        await callback.answer(
            "Запис не знайдено",
            show_alert=True,
        )
        return

    # 1. Видаляємо всі Google Calendar події.
    await delete_google_events(booking.get("calendar_event_id"))

    # 2. Повністю видаляємо запис із БД.
    deleted = await delete_booking_by_id(booking_id)

    if not deleted:
        await callback.answer(
            "❌ Не вдалося видалити запис.",
            show_alert=True,
        )
        return

    # 3. Повідомляємо клієнта.
    client_telegram_id = booking.get("client_telegram_id")

    if client_telegram_id:
        if booking.get("client_language") == "pt":
            client_text = (
                "❌ A sua marcação foi "
                "cancelada pela profissional.\n\n"
                f"Profissional: "
                f"{booking['master_name']}\n"
                f"Data: {booking['date']}\n"
                f"Hora: {booking['time']}\n\n"
                "Pode escolher outra data "
                "e hora no bot."
            )
        else:
            client_text = (
                "❌ Майстер скасував "
                "ваш запис.\n\n"
                f"👩 Майстер: "
                f"{booking['master_name']}\n"
                f"📅 Дата: "
                f"{booking['date']}\n"
                f"🕒 Час: "
                f"{booking['time']}\n\n"
                "Ви можете обрати іншу "
                "дату та час у боті."
            )

        try:
            await callback.bot.send_message(
                chat_id=client_telegram_id,
                text=client_text,
            )
        except Exception as error:
            print(
                "ADMIN CLIENT CANCEL " "NOTIFICATION ERROR:",
                repr(error),
            )

    await callback.message.answer(
        "❌ Запис скасовано.\n\n"
        "✅ Видалено з бази\n"
        "✅ Видалено з Google Calendar\n"
        "✅ Клієнту надіслано повідомлення",
        reply_markup=admin_bookings_menu_keyboard(),
    )

    await callback.answer()


@router.callback_query(F.data == "admin_bookings_back")
async def admin_bookings_back(
    callback: CallbackQuery,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "⛔ Немає доступу",
            show_alert=True,
        )
        return

    await callback.message.answer(
        "Адмін-панель:",
        reply_markup=admin_menu(),
    )

    await callback.answer()


@router.message(F.text == "/clear_bookings")
async def clear_bookings(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    await delete_all_bookings()

    await message.answer("🗑 Усі записи видалені.")
