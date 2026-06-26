from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS
from database.queries import (
    add_master,
    get_active_masters,
    get_all_masters,
    get_master_by_id,
    update_master,
    delete_master,
)
from keyboards.menus import admin_menu
from locales.ua import BUTTONS as UA_BUTTONS
from states.admin_state import AddMasterState, EditMasterState

router = Router()


def admin_masters_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["add_master"], callback_data="admin_add_master"
                )
            ],
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["edit_master"], callback_data="admin_edit_master"
                )
            ],
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["delete_master"],
                    callback_data="admin_delete_master",
                )
            ],
            [InlineKeyboardButton(text=UA_BUTTONS["back"], callback_data="admin_back")],
        ]
    )


def masters_choose_keyboard(masters, action: str):
    keyboard = []

    for master in masters:
        status = "✅" if master["is_active"] else "🚫"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {master['name']}",
                    callback_data=f"{action}:{master['id']}",
                )
            ]
        )

    keyboard.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_admin_masters")]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(F.text == UA_BUTTONS["admin_masters"])
async def admin_masters_menu(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас немає доступу.")
        return

    masters = await get_all_masters()

    if masters:
        masters_text = "\n".join(
            [
                f"{'✅' if master['is_active'] else '🚫'} {master['name']}"
                for master in masters
            ]
        )
    else:
        masters_text = "Поки що майстрів немає."

    await message.answer(
        "👩 Управління майстрами\n\n" f"Список майстрів:\n{masters_text}",
        reply_markup=admin_masters_keyboard(),
    )


@router.callback_query(F.data == "back_admin_masters")
async def back_admin_masters(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    masters = await get_all_masters()

    if masters:
        masters_text = "\n".join(
            [
                f"{'✅' if master['is_active'] else '🚫'} {master['name']}"
                for master in masters
            ]
        )
    else:
        masters_text = "Поки що майстрів немає."

    await callback.message.answer(
        "👩 Управління майстрами\n\n" f"Список майстрів:\n{masters_text}",
        reply_markup=admin_masters_keyboard(),
    )
    await callback.answer()


# ---------- ДОДАТИ МАЙСТРА ----------


@router.callback_query(F.data == "admin_add_master")
async def start_add_master(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    await state.clear()
    await state.set_state(AddMasterState.name)

    await callback.message.answer("➕ Додавання майстра\n\n" "Введіть ім’я майстра:")
    await callback.answer()


@router.message(AddMasterState.name)
async def add_master_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddMasterState.photo)

    await message.answer(
        "📸 Надішліть фото майстра.\n\n" "Якщо фото поки немає — напишіть: пропустити"
    )


@router.message(AddMasterState.photo)
async def add_master_photo(message: Message, state: FSMContext):
    photo_id = None

    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.text and message.text.lower() in ["пропустити", "skip"]:
        photo_id = None
    else:
        await message.answer("Надішліть фото або напишіть: пропустити")
        return

    await state.update_data(photo_id=photo_id)
    await state.set_state(AddMasterState.description_ua)

    await message.answer("🇺🇦 Введіть опис майстра українською:")


@router.message(AddMasterState.description_ua)
async def add_master_description_ua(message: Message, state: FSMContext):
    await state.update_data(description_ua=message.text)
    await state.set_state(AddMasterState.description_pt)

    await message.answer("🇵🇹 Введіть опис майстра португальською:")


@router.message(AddMasterState.description_pt)
async def add_master_description_pt(message: Message, state: FSMContext):
    await state.update_data(description_pt=message.text)
    await state.set_state(AddMasterState.telegram_id)

    await message.answer(
        "🆔 Введіть Telegram ID майстра.\n\n" "Якщо поки немає — напишіть: пропустити"
    )


@router.message(AddMasterState.telegram_id)
async def add_master_telegram_id(message: Message, state: FSMContext):
    if message.text.lower() in ["пропустити", "skip"]:
        telegram_id = None
    else:
        try:
            telegram_id = int(message.text)
        except ValueError:
            await message.answer("Telegram ID має бути числом або напишіть: пропустити")
            return

    await state.update_data(telegram_id=telegram_id)
    await state.set_state(AddMasterState.schedule)

    await message.answer(
        "🕒 Введіть графік роботи майстра.\n\n" "Наприклад: Пн-Сб 09:30–17:00"
    )


@router.message(AddMasterState.schedule)
async def add_master_schedule(message: Message, state: FSMContext):
    await state.update_data(schedule=message.text)
    await state.set_state(AddMasterState.calendar_id)

    await message.answer(
        "📅 Введіть Google Calendar ID майстра.\n\n"
        "Наприклад:\n"
        "marinettka026@gmail.com\n\n"
        "Якщо поки немає — напишіть: пропустити"
    )


@router.message(AddMasterState.calendar_id)
async def add_master_calendar_id(message: Message, state: FSMContext):
    if message.text.lower() in ["пропустити", "skip"]:
        calendar_id = None
    else:
        calendar_id = message.text.strip()

    await state.update_data(calendar_id=calendar_id)
    data = await state.get_data()

    await add_master(
        name=data["name"],
        telegram_id=data["telegram_id"],
        photo_id=data["photo_id"],
        description_ua=data["description_ua"],
        description_pt=data["description_pt"],
        schedule=data["schedule"],
        calendar_id=data["calendar_id"],
    )

    await state.clear()

    await message.answer(
        "✅ Майстра успішно додано!\n\n"
        f"Ім’я: {data['name']}\n"
        f"Calendar ID: {data['calendar_id'] or 'Не вказано'}",
        reply_markup=admin_menu(),
    )


# ---------- РЕДАГУВАТИ МАЙСТРА ----------


@router.callback_query(F.data == "admin_edit_master")
async def choose_master_to_edit(callback: CallbackQuery):
    masters = await get_all_masters()

    if not masters:
        await callback.message.answer("Поки що немає майстрів для редагування.")
        await callback.answer()
        return

    await callback.message.answer(
        "✏️ Оберіть майстра для редагування:",
        reply_markup=masters_choose_keyboard(masters, "edit_master"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_master:"))
async def start_edit_master(callback: CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split(":")[1])
    master = await get_master_by_id(master_id)

    if not master:
        await callback.answer("Майстра не знайдено", show_alert=True)
        return

    await state.clear()
    await state.update_data(master_id=master_id)
    await state.set_state(EditMasterState.name)

    await callback.message.answer(
        "✏️ Редагування майстра\n\n"
        f"Поточне ім’я: {master['name']}\n\n"
        "Введіть нове ім’я або напишіть: залишити"
    )
    await callback.answer()


@router.message(EditMasterState.name)
async def edit_master_name(message: Message, state: FSMContext):
    data = await state.get_data()
    master = await get_master_by_id(data["master_id"])

    name = master["name"] if message.text.lower() == "залишити" else message.text

    await state.update_data(name=name)
    await state.set_state(EditMasterState.photo)

    await message.answer(
        "📸 Надішліть нове фото.\n\n"
        "Або напишіть:\n"
        "залишити — залишити старе фото\n"
        "пропустити — прибрати фото"
    )


@router.message(EditMasterState.photo)
async def edit_master_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    master = await get_master_by_id(data["master_id"])

    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.text and message.text.lower() == "залишити":
        photo_id = master["photo_id"]
    elif message.text and message.text.lower() in ["пропустити", "skip"]:
        photo_id = None
    else:
        await message.answer("Надішліть фото або напишіть: залишити / пропустити")
        return

    await state.update_data(photo_id=photo_id)
    await state.set_state(EditMasterState.description_ua)

    await message.answer("🇺🇦 Введіть новий опис українською або напишіть: залишити")


@router.message(EditMasterState.description_ua)
async def edit_master_description_ua(message: Message, state: FSMContext):
    data = await state.get_data()
    master = await get_master_by_id(data["master_id"])

    description_ua = (
        master["description_ua"] if message.text.lower() == "залишити" else message.text
    )

    await state.update_data(description_ua=description_ua)
    await state.set_state(EditMasterState.description_pt)

    await message.answer("🇵🇹 Введіть новий опис португальською або напишіть: залишити")


@router.message(EditMasterState.description_pt)
async def edit_master_description_pt(message: Message, state: FSMContext):
    data = await state.get_data()
    master = await get_master_by_id(data["master_id"])

    description_pt = (
        master["description_pt"] if message.text.lower() == "залишити" else message.text
    )

    await state.update_data(description_pt=description_pt)
    await state.set_state(EditMasterState.telegram_id)

    await message.answer(
        "🆔 Введіть новий Telegram ID.\n\n"
        "Або напишіть:\n"
        "залишити — залишити старий ID\n"
        "пропустити — прибрати ID"
    )


@router.message(EditMasterState.telegram_id)
async def edit_master_telegram_id(message: Message, state: FSMContext):
    data = await state.get_data()
    master = await get_master_by_id(data["master_id"])

    if message.text.lower() == "залишити":
        telegram_id = master["telegram_id"]
    elif message.text.lower() in ["пропустити", "skip"]:
        telegram_id = None
    else:
        try:
            telegram_id = int(message.text)
        except ValueError:
            await message.answer(
                "Telegram ID має бути числом або напишіть: залишити / пропустити"
            )
            return

    await state.update_data(telegram_id=telegram_id)
    await state.set_state(EditMasterState.schedule)

    await message.answer("🕒 Введіть новий графік або напишіть: залишити")


@router.message(EditMasterState.schedule)
async def edit_master_schedule(message: Message, state: FSMContext):
    data = await state.get_data()
    master = await get_master_by_id(data["master_id"])

    schedule = (
        master["schedule"] if message.text.lower() == "залишити" else message.text
    )

    await update_master(
        master_id=data["master_id"],
        name=data["name"],
        telegram_id=data["telegram_id"],
        photo_id=data["photo_id"],
        description_ua=data["description_ua"],
        description_pt=data["description_pt"],
        schedule=schedule,
    )

    await state.clear()

    await message.answer(
        "✅ Дані майстра оновлено!",
        reply_markup=admin_menu(),
    )


# ---------- ВИМКНУТИ МАЙСТРА ----------


@router.callback_query(F.data == "admin_delete_master")
async def choose_master_to_delete(callback: CallbackQuery):
    masters = await get_all_masters()

    if not masters:
        await callback.message.answer("Поки що немає майстрів для вимкнення.")
        await callback.answer()
        return

    await callback.message.answer(
        "❌ Оберіть майстра, якого потрібно вимкнути:",
        reply_markup=masters_choose_keyboard(masters, "delete_master"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_master:"))
async def delete_master_handler(callback: CallbackQuery):
    master_id = int(callback.data.split(":")[1])

    await delete_master(master_id)

    await callback.message.answer(
        "🗑 Майстра видалено повністю.\n\n" "Також видалено його послуги.",
        reply_markup=admin_menu(),
    )

    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.answer(
        "Адмін-панель ZoYA Nails Studio\n\n" "Оберіть дію:",
        reply_markup=admin_menu(),
    )

    await callback.answer()
