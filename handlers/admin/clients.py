from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from database.queries import (
    get_clients_with_stats,
    get_client_by_id,
    update_client_note,
    set_client_blocked,
)
from keyboards.menus import admin_menu
from locales.ua import BUTTONS as UA_BUTTONS
from states.admin_state import ClientNoteState

router = Router()


def clients_keyboard(clients):
    keyboard = []

    for client in clients:
        status = "🚫" if client["is_blocked"] else "👤"
        name = client["name"] or "Без імені"
        bookings_count = client["bookings_count"]

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {name} | записів: {bookings_count}",
                    callback_data=f"client_card:{client['id']}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="clients_back_admin",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def client_card_keyboard(client):
    client_id = client["id"]
    telegram_id = client["telegram_id"]

    block_text = "✅ Розблокувати" if client["is_blocked"] else "🚫 Заблокувати"
    block_action = "unblock_client" if client["is_blocked"] else "block_client"

    keyboard = [
        [
            InlineKeyboardButton(
                text="💬 Написати клієнту",
                url=f"tg://user?id={telegram_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Додати / змінити нотатку",
                callback_data=f"client_note:{client_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=block_text,
                callback_data=f"{block_action}:{client_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Назад до клієнтів",
                callback_data="clients_list",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(F.text == UA_BUTTONS["admin_clients"])
async def admin_clients(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас немає доступу.")
        return

    clients = await get_clients_with_stats()

    if not clients:
        await message.answer(
            "👥 Клієнти\n\n" "Поки що клієнтів немає.",
            reply_markup=admin_menu(),
        )
        return

    await message.answer(
        "👥 База клієнтів\n\n" "Оберіть клієнта:",
        reply_markup=clients_keyboard(clients),
    )


@router.callback_query(F.data == "clients_list")
async def clients_list(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    clients = await get_clients_with_stats()

    await callback.message.answer(
        "👥 База клієнтів\n\n" "Оберіть клієнта:",
        reply_markup=clients_keyboard(clients),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("client_card:"))
async def client_card(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    client_id = int(callback.data.split(":")[1])
    client = await get_client_by_id(client_id)

    if not client:
        await callback.answer("Клієнта не знайдено", show_alert=True)
        return

    status = "🚫 Заблокований" if client["is_blocked"] else "✅ Активний"

    text = (
        "👤 Картка клієнта\n\n"
        f"Ім’я: {client['name'] or 'Не вказано'}\n"
        f"Телефон: {client['phone'] or 'Не вказано'}\n"
        f"Telegram ID: {client['telegram_id']}\n"
        f"Мова: {client['language']}\n"
        f"Статус: {status}\n"
        f"Кількість записів: {client['bookings_count']}\n\n"
        f"📝 Нотатка:\n{client['note'] or 'Немає нотатки'}"
    )

    await callback.message.answer(
        text,
        reply_markup=client_card_keyboard(client),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("client_note:"))
async def client_note_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    client_id = int(callback.data.split(":")[1])

    await state.update_data(client_id=client_id)
    await state.set_state(ClientNoteState.waiting_note)

    await callback.message.answer(
        "📝 Введіть нотатку про клієнта:\n\n"
        "Наприклад: любить нюдовий манікюр, алергія на матеріал, часто переносить записи."
    )

    await callback.answer()


@router.message(ClientNoteState.waiting_note)
async def client_note_save(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    data = await state.get_data()
    client_id = data["client_id"]

    await update_client_note(client_id, message.text)
    await state.clear()

    client = await get_client_by_id(client_id)

    await message.answer(
        "✅ Нотатку збережено.",
        reply_markup=client_card_keyboard(client),
    )


@router.callback_query(F.data.startswith("block_client:"))
async def block_client(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    client_id = int(callback.data.split(":")[1])

    await set_client_blocked(client_id, 1)

    await callback.message.answer("🚫 Клієнта заблоковано.")
    await callback.answer()


@router.callback_query(F.data.startswith("unblock_client:"))
async def unblock_client(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    client_id = int(callback.data.split(":")[1])

    await set_client_blocked(client_id, 0)

    await callback.message.answer("✅ Клієнта розблоковано.")
    await callback.answer()


@router.callback_query(F.data == "clients_back_admin")
async def clients_back_admin(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    await callback.message.answer(
        "Адмін-панель:",
        reply_markup=admin_menu(),
    )

    await callback.answer()
