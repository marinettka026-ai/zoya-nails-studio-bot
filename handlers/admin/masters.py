from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from database.queries import (
    add_master,
    get_active_masters,
    get_all_masters,
    get_master_by_id,
    get_master_schedule_exception,
    get_master_schedule_exceptions,
    set_master_schedule_exception,
    close_master_schedule_period,
    delete_master_schedule_exception,
    update_master,
    delete_master,
    get_services_by_master,
    add_service,
    update_service,
    deactivate_service,
    add_service_extra,
    get_service_extras_by_category,
)
from keyboards.menus import admin_menu
from locales.ua import BUTTONS as UA_BUTTONS
from states.admin_state import AddMasterState, EditMasterState

from datetime import datetime, time
from zoneinfo import ZoneInfo

from services.calendar import get_calendar_service

router = Router()


def admin_masters_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["add_master"],
                    callback_data="admin_add_master",
                )
            ],
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["edit_master"],
                    callback_data="admin_edit_master",
                )
            ],
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["delete_master"],
                    callback_data="admin_delete_master",
                )
            ],
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["back"],
                    callback_data="admin_back",
                )
            ],
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
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="back_admin_masters",
            )
        ]
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
        await callback.answer(
            "⛔ Немає доступу",
            show_alert=True,
        )
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

    elif message.text and message.text.lower() in [
        "пропустити",
        "skip",
    ]:
        photo_id = None

    else:
        await message.answer("Надішліть фото або напишіть: пропустити")
        return

    await state.update_data(photo_id=photo_id)
    await state.set_state(AddMasterState.description_ua)

    await message.answer("🇺🇦 Введіть опис майстра українською:")


@router.message(AddMasterState.description_ua)
async def add_master_description_ua(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        description_ua=message.text,
    )

    await state.set_state(
        AddMasterState.description_pt,
    )

    await message.answer("🇵🇹 Введіть опис майстра португальською:")


@router.message(AddMasterState.description_pt)
async def add_master_description_pt(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        description_pt=message.text,
    )

    await state.set_state(
        AddMasterState.telegram_id,
    )

    await message.answer(
        "🆔 Введіть Telegram ID майстра.\n\n" "Якщо поки немає — напишіть: пропустити"
    )


@router.message(AddMasterState.telegram_id)
async def add_master_telegram_id(
    message: Message,
    state: FSMContext,
):
    if message.text.lower() in [
        "пропустити",
        "skip",
    ]:
        telegram_id = None

    else:
        try:
            telegram_id = int(message.text)

        except ValueError:
            await message.answer(
                "Telegram ID має бути числом " "або напишіть: пропустити"
            )
            return

    await state.update_data(
        telegram_id=telegram_id,
    )

    await state.set_state(
        AddMasterState.schedule,
    )

    await message.answer(
        "🕒 Введіть графік роботи майстра.\n\n"
        "Приклад:\n"
        "Пн: 08:30-18:30\n"
        "Вт: 08:30-18:30\n"
        "Ср: 08:30-18:30\n"
        "Чт: 08:30-18:30\n"
        "Пт: 08:30-18:30\n"
        "Сб: вихідний\n"
        "Нд: вихідний"
    )


@router.message(AddMasterState.schedule)
async def add_master_schedule(
    message: Message,
    state: FSMContext,
):
    await state.update_data(
        schedule=message.text,
    )

    await state.set_state(
        AddMasterState.calendar_id,
    )

    await message.answer(
        "📅 Введіть Google Calendar ID майстра.\n\n"
        "Наприклад:\n"
        "marinettka026@gmail.com\n\n"
        "Якщо поки немає — напишіть: пропустити"
    )


@router.message(AddMasterState.calendar_id)
async def add_master_calendar_id(
    message: Message,
    state: FSMContext,
):
    if message.text.lower() in [
        "пропустити",
        "skip",
    ]:
        calendar_id = None

    else:
        calendar_id = message.text.strip()

    await state.update_data(
        calendar_id=calendar_id,
    )

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
        f"Calendar ID: "
        f"{data['calendar_id'] or 'Не вказано'}",
        reply_markup=admin_menu(),
    )


# ---------- РЕДАГУВАТИ МАЙСТРА ----------


class MasterScheduleExceptionState(StatesGroup):
    choosing_date = State()
    entering_hours = State()
    entering_period = State()
    deleting_date = State()


def schedule_exceptions_keyboard(master_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Змінити конкретну дату",
                    callback_data=f"master_exception_date:{master_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏖 Закрити період / відпустка",
                    callback_data=f"master_exception_period:{master_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Показати винятки",
                    callback_data=f"master_exception_list:{master_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Прибрати виняток",
                    callback_data=f"master_exception_delete:{master_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ До редагування майстра",
                    callback_data=f"edit_master:{master_id}",
                )
            ],
        ]
    )


def schedule_exception_action_keyboard(master_id: int, selected_date: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚫 Закрити весь день",
                    callback_data=f"master_exception_close:{master_id}:{selected_date}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🕒 Встановити години",
                    callback_data=f"master_exception_hours:{master_id}:{selected_date}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Повернути звичайний графік",
                    callback_data=f"master_exception_reset:{master_id}:{selected_date}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"master_exceptions:{master_id}",
                )
            ],
        ]
    )


async def show_schedule_exceptions_menu(
    message: Message, master_id: int, state: FSMContext
):
    master = await get_master_by_id(master_id)
    await state.clear()

    if not master:
        await message.answer("❌ Майстра не знайдено.")
        return

    await message.answer(
        f"📆 Винятки графіка — {master['name']}\n\n"
        "Тут можна змінити графік лише на конкретну дату, "
        "не змінюючи постійний тижневий розклад.\n\n"
        "• закрити окремий день;\n"
        "• відкрити вихідний або змінити години;\n"
        "• закрити цілий період відпустки;\n"
        "• повернути дату до звичайного графіка.",
        reply_markup=schedule_exceptions_keyboard(master_id),
    )


def _parse_admin_date(value: str):
    value = value.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_hours_range(value: str):
    value = value.strip().replace("–", "-").replace("—", "-")
    if "-" not in value:
        return None

    start_value, end_value = [part.strip() for part in value.split("-", 1)]

    try:
        start_dt = datetime.strptime(start_value, "%H:%M")
        end_dt = datetime.strptime(end_value, "%H:%M")
    except ValueError:
        return None

    if start_dt >= end_dt:
        return None

    return start_dt.strftime("%H:%M"), end_dt.strftime("%H:%M")


def master_edit_keyboard(master_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 Ім’я",
                    callback_data=f"edit_master_field:name:{master_id}",
                ),
                InlineKeyboardButton(
                    text="📸 Фото",
                    callback_data=f"edit_master_field:photo:{master_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🇺🇦 Опис UA",
                    callback_data=f"edit_master_field:description_ua:{master_id}",
                ),
                InlineKeyboardButton(
                    text="🇵🇹 Опис PT",
                    callback_data=f"edit_master_field:description_pt:{master_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🆔 Telegram ID",
                    callback_data=f"edit_master_field:telegram_id:{master_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🕒 Графік",
                    callback_data=f"edit_master_field:schedule:{master_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📅 Google Calendar ID",
                    callback_data=f"edit_master_field:calendar_id:{master_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📆 Винятки графіка",
                    callback_data=f"master_exceptions:{master_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ До вибору майстра",
                    callback_data="admin_edit_master",
                ),
            ],
        ]
    )


def master_edit_text(master):
    telegram_id = master["telegram_id"] or "Не вказано"
    calendar_id = master["calendar_id"] or "Не вказано"
    description_ua = master["description_ua"] or "Не вказано"
    description_pt = master["description_pt"] or "Не вказано"
    schedule = master["schedule"] or "Не вказано"
    photo_status = "Є" if master["photo_id"] else "Немає"

    return (
        "✏️ Редагування майстра\n\n"
        f"👤 Ім’я: {master['name']}\n"
        f"📸 Фото: {photo_status}\n"
        f"🆔 Telegram ID: {telegram_id}\n"
        f"📅 Calendar ID: {calendar_id}\n\n"
        f"🇺🇦 Опис UA:\n{description_ua}\n\n"
        f"🇵🇹 Опис PT:\n{description_pt}\n\n"
        f"🕒 Графік:\n{schedule}\n\n"
        "Що саме потрібно змінити?"
    )


async def show_master_edit_menu(message: Message, master_id: int, state: FSMContext):
    master = await get_master_by_id(master_id)

    if not master:
        await state.clear()
        await message.answer("❌ Майстра не знайдено.")
        return

    await state.clear()
    await state.update_data(master_id=master_id)

    await message.answer(
        master_edit_text(master),
        reply_markup=master_edit_keyboard(master_id),
    )


async def save_master_field(master_id: int, field_name: str, value):
    master = await get_master_by_id(master_id)

    if not master:
        return False

    master_data = {
        "name": master["name"],
        "telegram_id": master["telegram_id"],
        "photo_id": master["photo_id"],
        "description_ua": master["description_ua"],
        "description_pt": master["description_pt"],
        "schedule": master["schedule"],
        "calendar_id": master["calendar_id"],
    }

    master_data[field_name] = value

    await update_master(
        master_id=master_id,
        name=master_data["name"],
        telegram_id=master_data["telegram_id"],
        photo_id=master_data["photo_id"],
        description_ua=master_data["description_ua"],
        description_pt=master_data["description_pt"],
        schedule=master_data["schedule"],
        calendar_id=master_data["calendar_id"],
    )

    return True


@router.callback_query(F.data == "admin_edit_master")
async def choose_master_to_edit(
    callback: CallbackQuery,
    state: FSMContext,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    await state.clear()
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
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    try:
        master_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Некоректний ID майстра", show_alert=True)
        return

    master = await get_master_by_id(master_id)

    if not master:
        await callback.answer("Майстра не знайдено", show_alert=True)
        return

    await state.clear()
    await state.update_data(master_id=master_id)

    await callback.message.answer(
        master_edit_text(master),
        reply_markup=master_edit_keyboard(master_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_master_field:"))
async def choose_master_field_to_edit(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    try:
        _, field_name, master_id_raw = callback.data.split(":")
        master_id = int(master_id_raw)
    except (ValueError, IndexError):
        await callback.answer("❌ Некоректні дані", show_alert=True)
        return

    master = await get_master_by_id(master_id)

    if not master:
        await callback.answer("Майстра не знайдено", show_alert=True)
        return

    await state.clear()
    await state.update_data(master_id=master_id)

    if field_name == "name":
        await state.set_state(EditMasterState.name)
        await callback.message.answer(
            "👤 Зміна імені майстра\n\n"
            f"Поточне ім’я: {master['name']}\n\n"
            "Введіть нове ім’я:"
        )
    elif field_name == "photo":
        await state.set_state(EditMasterState.photo)
        await callback.message.answer(
            "📸 Зміна фото майстра\n\n"
            "Надішліть нове фото.\n\n"
            "Щоб прибрати поточне фото — напишіть:\n"
            "пропустити"
        )
    elif field_name == "description_ua":
        await state.set_state(EditMasterState.description_ua)
        await callback.message.answer(
            "🇺🇦 Зміна опису українською\n\n"
            f"Поточний опис:\n{master['description_ua'] or 'Не вказано'}\n\n"
            "Введіть новий опис:"
        )
    elif field_name == "description_pt":
        await state.set_state(EditMasterState.description_pt)
        await callback.message.answer(
            "🇵🇹 Зміна опису португальською\n\n"
            f"Поточний опис:\n{master['description_pt'] or 'Не вказано'}\n\n"
            "Введіть новий опис:"
        )
    elif field_name == "telegram_id":
        await state.set_state(EditMasterState.telegram_id)
        await callback.message.answer(
            "🆔 Зміна Telegram ID\n\n"
            f"Поточний Telegram ID:\n{master['telegram_id'] or 'Не вказано'}\n\n"
            "Введіть новий Telegram ID.\n\n"
            "Щоб прибрати ID — напишіть:\n"
            "пропустити"
        )
    elif field_name == "schedule":
        await state.set_state(EditMasterState.schedule)
        await callback.message.answer(
            "🕒 Зміна графіка роботи\n\n"
            f"Поточний графік:\n{master['schedule'] or 'Не вказано'}\n\n"
            "Введіть новий графік.\n\n"
            "Приклад:\n"
            "Пн: 08:30-18:30\n"
            "Вт: 08:30-18:30\n"
            "Ср: 08:30-18:30\n"
            "Чт: 08:30-18:30\n"
            "Пт: 08:30-18:30\n"
            "Сб: вихідний\n"
            "Нд: вихідний"
        )
    elif field_name == "calendar_id":
        await state.set_state(EditMasterState.calendar_id)
        await callback.message.answer(
            "📅 Зміна Google Calendar ID\n\n"
            f"Поточний Calendar ID:\n{master['calendar_id'] or 'Не вказано'}\n\n"
            "Введіть новий Google Calendar ID.\n\n"
            "Щоб прибрати Calendar ID — напишіть:\n"
            "пропустити"
        )
    else:
        await callback.answer("❌ Невідоме поле", show_alert=True)
        return

    await callback.answer()


@router.message(EditMasterState.name)
async def edit_master_name(message: Message, state: FSMContext):
    data = await state.get_data()
    master_id = data.get("master_id")

    if not master_id:
        await state.clear()
        await message.answer("❌ Не вдалося визначити майстра.")
        return

    if not message.text or not message.text.strip():
        await message.answer("Введіть ім’я майстра.")
        return

    saved = await save_master_field(master_id, "name", message.text.strip())

    if not saved:
        await state.clear()
        await message.answer("❌ Майстра не знайдено.")
        return

    await message.answer("✅ Ім’я майстра оновлено.")
    await show_master_edit_menu(message, master_id, state)


@router.message(EditMasterState.photo)
async def edit_master_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    master_id = data.get("master_id")

    if not master_id:
        await state.clear()
        await message.answer("❌ Не вдалося визначити майстра.")
        return

    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.text and message.text.strip().lower() in ["пропустити", "skip"]:
        photo_id = None
    else:
        await message.answer("Надішліть нове фото або напишіть: пропустити")
        return

    saved = await save_master_field(master_id, "photo_id", photo_id)

    if not saved:
        await state.clear()
        await message.answer("❌ Майстра не знайдено.")
        return

    await message.answer(
        "✅ Фото майстра оновлено." if photo_id else "✅ Фото майстра прибрано."
    )
    await show_master_edit_menu(message, master_id, state)


@router.message(EditMasterState.description_ua)
async def edit_master_description_ua(message: Message, state: FSMContext):
    data = await state.get_data()
    master_id = data.get("master_id")

    if not master_id:
        await state.clear()
        await message.answer("❌ Не вдалося визначити майстра.")
        return

    if not message.text:
        await message.answer("Введіть опис майстра українською.")
        return

    saved = await save_master_field(master_id, "description_ua", message.text.strip())

    if not saved:
        await state.clear()
        await message.answer("❌ Майстра не знайдено.")
        return

    await message.answer("✅ Опис українською оновлено.")
    await show_master_edit_menu(message, master_id, state)


@router.message(EditMasterState.description_pt)
async def edit_master_description_pt(message: Message, state: FSMContext):
    data = await state.get_data()
    master_id = data.get("master_id")

    if not master_id:
        await state.clear()
        await message.answer("❌ Не вдалося визначити майстра.")
        return

    if not message.text:
        await message.answer("Введіть опис майстра португальською.")
        return

    saved = await save_master_field(master_id, "description_pt", message.text.strip())

    if not saved:
        await state.clear()
        await message.answer("❌ Майстра не знайдено.")
        return

    await message.answer("✅ Опис португальською оновлено.")
    await show_master_edit_menu(message, master_id, state)


@router.message(EditMasterState.telegram_id)
async def edit_master_telegram_id(message: Message, state: FSMContext):
    data = await state.get_data()
    master_id = data.get("master_id")

    if not master_id:
        await state.clear()
        await message.answer("❌ Не вдалося визначити майстра.")
        return

    if not message.text:
        await message.answer("Введіть Telegram ID або напишіть: пропустити")
        return

    text = message.text.strip()

    if text.lower() in ["пропустити", "skip"]:
        telegram_id = None
    else:
        try:
            telegram_id = int(text)
        except ValueError:
            await message.answer("Telegram ID має бути числом або напишіть: пропустити")
            return

    saved = await save_master_field(master_id, "telegram_id", telegram_id)

    if not saved:
        await state.clear()
        await message.answer("❌ Майстра не знайдено.")
        return

    await message.answer("✅ Telegram ID оновлено.")
    await show_master_edit_menu(message, master_id, state)


@router.message(EditMasterState.schedule)
async def edit_master_schedule(message: Message, state: FSMContext):
    data = await state.get_data()
    master_id = data.get("master_id")

    if not master_id:
        await state.clear()
        await message.answer("❌ Не вдалося визначити майстра.")
        return

    if not message.text or not message.text.strip():
        await message.answer("Введіть новий графік роботи.")
        return

    saved = await save_master_field(master_id, "schedule", message.text.strip())

    if not saved:
        await state.clear()
        await message.answer("❌ Майстра не знайдено.")
        return

    await message.answer("✅ Графік роботи оновлено.")
    await show_master_edit_menu(message, master_id, state)


@router.message(EditMasterState.calendar_id)
async def edit_master_calendar_id(message: Message, state: FSMContext):
    data = await state.get_data()
    master_id = data.get("master_id")

    if not master_id:
        await state.clear()
        await message.answer("❌ Не вдалося визначити майстра.")
        return

    if not message.text:
        await message.answer("Введіть Google Calendar ID або напишіть: пропустити")
        return

    text = message.text.strip()
    calendar_id = None if text.lower() in ["пропустити", "skip"] else text

    saved = await save_master_field(master_id, "calendar_id", calendar_id)

    if not saved:
        await state.clear()
        await message.answer("❌ Майстра не знайдено.")
        return

    await message.answer("✅ Google Calendar ID оновлено.")
    await show_master_edit_menu(message, master_id, state)


# ---------- ВИМКНУТИ МАЙСТРА ----------


@router.callback_query(F.data == "admin_delete_master")
async def choose_master_to_delete(
    callback: CallbackQuery,
):
    masters = await get_all_masters()

    if not masters:
        await callback.message.answer("Поки що немає майстрів для вимкнення.")

        await callback.answer()
        return

    await callback.message.answer(
        "❌ Оберіть майстра, якого потрібно вимкнути:",
        reply_markup=masters_choose_keyboard(
            masters,
            "delete_master",
        ),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("delete_master:"))
async def delete_master_handler(
    callback: CallbackQuery,
):
    master_id = int(callback.data.split(":")[1])

    await delete_master(master_id)

    await callback.message.answer(
        "🗑 Майстра видалено повністю.\n\n" "Також видалено його послуги.",
        reply_markup=admin_menu(),
    )

    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    await callback.message.answer(
        "Адмін-панель ZoYA Nails Studio\n\n" "Оберіть дію:",
        reply_markup=admin_menu(),
    )

    await callback.answer()


@router.message(F.text == "/masters_ids")
async def show_master_ids(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    masters = await get_all_masters()

    if not masters:
        await message.answer("Майстрів не знайдено.")
        return

    text = "👩‍💼 Майстри:\n\n"

    for master in masters:
        text += f"ID: {master['id']} — " f"{master['name']}\n"

    await message.answer(text)


@router.message(F.text == "/copy_services")
async def copy_zoya_services_to_nastya(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    SOURCE_MASTER_ID = 2  # Zoya
    TARGET_MASTER_ID = 7  # Nastya
    PRICE_DISCOUNT = 10

    source_master = await get_master_by_id(SOURCE_MASTER_ID)
    target_master = await get_master_by_id(TARGET_MASTER_ID)

    if not source_master or not target_master:
        await message.answer("❌ Не вдалося знайти Zoya або Nastya в базі.")
        return

    source_services = await get_services_by_master(SOURCE_MASTER_ID)

    if not source_services:
        await message.answer("❌ У Zoya немає активних послуг для копіювання.")
        return

    target_services = await get_services_by_master(TARGET_MASTER_ID)

    existing_keys = {
        (
            (service["name_ua"] or "").strip().lower(),
            (service["category_ua"] or "").strip().lower(),
        )
        for service in target_services
    }

    copied = 0
    skipped = 0

    for service in source_services:
        service_key = (
            (service["name_ua"] or "").strip().lower(),
            (service["category_ua"] or "").strip().lower(),
        )

        if service_key in existing_keys:
            skipped += 1
            continue

        old_price = float(service["price"] or 0)
        new_price = max(0, old_price - PRICE_DISCOUNT)

        await add_service(
            master_id=TARGET_MASTER_ID,
            name_ua=service["name_ua"],
            name_pt=service["name_pt"],
            description_ua=service["description_ua"],
            description_pt=service["description_pt"],
            category_ua=service["category_ua"],
            category_pt=service["category_pt"],
            price=new_price,
            duration=int(service["duration"] or 0),
            deposit_amount=float(service["deposit_amount"] or 0),
            resource_type=service["resource_type"] or "manicure",
        )

        existing_keys.add(service_key)
        copied += 1

    await message.answer(
        "✅ Копіювання завершено.\n\n"
        f"Звідки: {source_master['name']} (ID {SOURCE_MASTER_ID})\n"
        f"Куди: {target_master['name']} (ID {TARGET_MASTER_ID})\n"
        f"Знижка для Nastya: -{PRICE_DISCOUNT} €\n\n"
        f"Скопійовано: {copied}\n"
        f"Пропущено як дублікати: {skipped}"
    )


@router.message(F.text == "/update_nastya_price")
async def update_nastya_price(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    NASTYA_ID = 7

    nastya = await get_master_by_id(NASTYA_ID)
    if not nastya:
        await message.answer("❌ Nastya (ID 7) не знайдена.")
        return

    services = await get_services_by_master(NASTYA_ID)

    if not services:
        await message.answer("❌ У Nastya немає активних послуг.")
        return

    def normalize(value):
        return (value or "").strip().lower()

    async def update_main_service(
        service,
        *,
        price=None,
        duration=None,
        description_ua=None,
        description_pt=None,
    ):
        await update_service(
            service_id=service["id"],
            category_ua=service["category_ua"],
            category_pt=service["category_pt"],
            name_ua=service["name_ua"],
            name_pt=service["name_pt"],
            description_ua=(
                description_ua
                if description_ua is not None
                else service["description_ua"]
            ),
            description_pt=(
                description_pt
                if description_pt is not None
                else service["description_pt"]
            ),
            price=price if price is not None else service["price"],
            duration=duration if duration is not None else service["duration"],
            deposit_amount=(
                service["deposit_amount"]
                if service["deposit_amount"] is not None
                else 0
            ),
        )

    updated = []
    deactivated = []
    added_extras = []
    skipped_extras = []

    # --- Основні послуги Nastya ---

    price_updates = {
        "японський манікюр (p.shine)": 35.0,
        "частковий педикюр (пальчики) + гель-лак": 45.0,
        "гігієнічний манікюр": 25.0,
        "манікюр з покриттям гель-лак": 45.0,
        "гігієнічний педикюр": 35.0,
        "педикюр з покриттям гель-лак": 50.0,
        "чоловічий манікюр": 30.0,
        "манікюр чоловічий": 30.0,
        "чоловічий педикюр": 40.0,
        "педикюр чоловічий": 40.0,
    }

    complex_note_ua = (
        "Зняття покриття у комплексі та ремонт декількох нігтів "
        "враховані у вартість комплексної послуги й додатково не оплачуються."
    )
    complex_note_pt = (
        "A remoção do revestimento dentro do serviço completo e a reparação "
        "de algumas unhas estão incluídas no valor e não são cobradas à parte."
    )

    for service in services:
        name_key = normalize(service["name_ua"])

        if name_key in price_updates:
            new_description_ua = None
            new_description_pt = None

            if name_key in {
                "манікюр з покриттям гель-лак",
                "педикюр з покриттям гель-лак",
            }:
                current_ua = (service["description_ua"] or "").strip()
                current_pt = (service["description_pt"] or "").strip()

                if complex_note_ua not in current_ua:
                    new_description_ua = (
                        f"{current_ua}\n\n{complex_note_ua}"
                        if current_ua
                        else complex_note_ua
                    )

                if complex_note_pt not in current_pt:
                    new_description_pt = (
                        f"{current_pt}\n\n{complex_note_pt}"
                        if current_pt
                        else complex_note_pt
                    )

            await update_main_service(
                service,
                price=price_updates[name_key],
                description_ua=new_description_ua,
                description_pt=new_description_pt,
            )
            updated.append(f"{service['name_ua']} → {price_updates[name_key]}€")

        if name_key == "зняття покриття без подальшого покриття":
            await deactivate_service(service["id"])
            deactivated.append(service["name_ua"])

    # --- Додаткові послуги Nastya ---

    extras_to_add = [
        {
            "category_ua": "Манікюр жіночий",
            "category_pt": "Manicure feminina",
            "name_ua": "Дизайн одного нігтя",
            "name_pt": "Design de uma unha",
            "price": 0.0,
            "duration": 0,
        },
        {
            "category_ua": "Манікюр жіночий",
            "category_pt": "Manicure feminina",
            "name_ua": "Дизайн на всі нігті",
            "name_pt": "Design em todas as unhas",
            "price": 10.0,
            "duration": 30,
        },
        {
            "category_ua": "Манікюр жіночий",
            "category_pt": "Manicure feminina",
            "name_ua": "Френч",
            "name_pt": "Francesinha",
            "price": 10.0,
            "duration": 15,
        },
        {
            "category_ua": "Педикюр жіночий",
            "category_pt": "Pedicure feminina",
            "name_ua": "Покриття звичайним лаком",
            "name_pt": "Aplicação de verniz tradicional",
            "price": 10.0,
            "duration": 15,
        },
        {
            "category_ua": "Педикюр жіночий",
            "category_pt": "Pedicure feminina",
            "name_ua": "Зняття гель-покриття без подальшого покриття",
            "name_pt": "Remoção de verniz gel sem nova aplicação",
            "price": 5.0,
            "duration": 0,
        },
        {
            "category_ua": "Педикюр жіночий",
            "category_pt": "Pedicure feminina",
            "name_ua": "SPA догляд для ніг від Baehr",
            "name_pt": "Cuidado SPA para os pés Baehr",
            "price": 10.0,
            "duration": 20,
        },
        {
            "category_ua": "Чоловічий манікюр та педикюр",
            "category_pt": "Manicure e pedicure masculina",
            "name_ua": "SPA догляд від Baehr",
            "name_pt": "Cuidado SPA Baehr",
            "price": 10.0,
            "duration": 20,
        },
    ]

    categories = {item["category_ua"] for item in extras_to_add}

    existing_extra_keys = set()

    for category_ua in categories:
        existing_extras = await get_service_extras_by_category(
            NASTYA_ID,
            category_ua,
        )

        for extra in existing_extras:
            existing_extra_keys.add(
                (
                    normalize(extra["category_ua"]),
                    normalize(extra["name_ua"]),
                )
            )

    for extra in extras_to_add:
        key = (
            normalize(extra["category_ua"]),
            normalize(extra["name_ua"]),
        )

        if key in existing_extra_keys:
            skipped_extras.append(extra["name_ua"])
            continue

        await add_service_extra(
            master_id=NASTYA_ID,
            category_ua=extra["category_ua"],
            category_pt=extra["category_pt"],
            name_ua=extra["name_ua"],
            name_pt=extra["name_pt"],
            price=extra["price"],
            duration=extra["duration"],
        )

        existing_extra_keys.add(key)
        added_extras.append(extra["name_ua"])

    result_lines = [
        "✅ Прайс Nastya оновлено.",
        "",
        f"Основних послуг оновлено: {len(updated)}",
        f"Основних послуг вимкнено: {len(deactivated)}",
        f"Додаткових послуг додано: {len(added_extras)}",
        f"Дублікатів extras пропущено: {len(skipped_extras)}",
    ]

    if updated:
        result_lines.append("")
        result_lines.append("💶 Оновлено:")
        result_lines.extend(f"• {item}" for item in updated)

    if deactivated:
        result_lines.append("")
        result_lines.append("🚫 Вимкнено:")
        result_lines.extend(f"• {item}" for item in deactivated)

    if added_extras:
        result_lines.append("")
        result_lines.append("✨ Додано:")
        result_lines.extend(f"• {item}" for item in added_extras)

    await message.answer("\n".join(result_lines))


@router.callback_query(F.data.startswith("master_exceptions:"))
async def master_exceptions_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return
    master_id = int(callback.data.split(":", 1)[1])
    await show_schedule_exceptions_menu(callback.message, master_id, state)
    await callback.answer()


@router.callback_query(F.data.startswith("master_exception_date:"))
async def master_exception_date_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return
    master_id = int(callback.data.split(":", 1)[1])
    await state.clear()
    await state.update_data(exception_master_id=master_id)
    await state.set_state(MasterScheduleExceptionState.choosing_date)
    await callback.message.answer("📅 Введіть дату.\\n\\nНаприклад: 28.09.2026")
    await callback.answer()


@router.message(MasterScheduleExceptionState.choosing_date)
async def master_exception_date_received(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    selected = _parse_admin_date(message.text or "")
    if not selected:
        await message.answer("❌ Невірна дата. Приклад: 28.09.2026")
        return

    data = await state.get_data()
    master_id = data["exception_master_id"]
    selected_date = selected.strftime("%Y-%m-%d")
    existing = await get_master_schedule_exception(master_id, selected_date)

    if existing:
        if existing["is_working"]:
            current = f"Зараз: 🟢 {existing['start_time']}–{existing['end_time']}"
        else:
            current = "Зараз: 🚫 день закритий"
    else:
        current = "Винятку немає — діє звичайний тижневий графік."

    await message.answer(
        f"📅 {selected.strftime('%d.%m.%Y')}\\n\\n{current}\\n\\nЩо зробити?",
        reply_markup=schedule_exception_action_keyboard(master_id, selected_date),
    )


@router.callback_query(F.data.startswith("master_exception_close:"))
async def master_exception_close_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return
    _, master_id, selected_date = callback.data.split(":", 2)
    master_id = int(master_id)
    await set_master_schedule_exception(master_id, selected_date, False)
    shown = datetime.strptime(selected_date, "%Y-%m-%d").strftime("%d.%m.%Y")
    await callback.message.answer(f"✅ {shown} повністю закрито для онлайн-запису.")
    await show_schedule_exceptions_menu(callback.message, master_id, state)
    await callback.answer()


@router.callback_query(F.data.startswith("master_exception_hours:"))
async def master_exception_hours_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return
    _, master_id, selected_date = callback.data.split(":", 2)
    await state.clear()
    await state.update_data(
        exception_master_id=int(master_id),
        exception_date=selected_date,
    )
    await state.set_state(MasterScheduleExceptionState.entering_hours)
    await callback.message.answer(
        "🕒 Введіть години для цієї дати.\\n\\n"
        "Наприклад: 14:00-18:30\\n\\n"
        "Так можна відкрити навіть звичайний вихідний."
    )
    await callback.answer()


@router.message(MasterScheduleExceptionState.entering_hours)
async def master_exception_hours_received(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    parsed = _parse_hours_range(message.text or "")
    if not parsed:
        await message.answer("❌ Невірний формат. Приклад: 14:00-18:30")
        return

    start_time_value, end_time_value = parsed
    data = await state.get_data()
    master_id = data["exception_master_id"]
    selected_date = data["exception_date"]

    await set_master_schedule_exception(
        master_id,
        selected_date,
        True,
        start_time_value,
        end_time_value,
    )
    shown = datetime.strptime(selected_date, "%Y-%m-%d").strftime("%d.%m.%Y")
    await message.answer(
        f"✅ {shown} відкрито для запису {start_time_value}–{end_time_value}."
    )
    await show_schedule_exceptions_menu(message, master_id, state)


@router.callback_query(F.data.startswith("master_exception_reset:"))
async def master_exception_reset_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return
    _, master_id, selected_date = callback.data.split(":", 2)
    master_id = int(master_id)
    deleted = await delete_master_schedule_exception(master_id, selected_date)
    await callback.message.answer(
        "✅ Виняток прибрано. Знову діє звичайний тижневий графік."
        if deleted
        else "ℹ️ Для цієї дати винятку не було."
    )
    await show_schedule_exceptions_menu(callback.message, master_id, state)
    await callback.answer()


@router.callback_query(F.data.startswith("master_exception_period:"))
async def master_exception_period_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return
    master_id = int(callback.data.split(":", 1)[1])
    await state.clear()
    await state.update_data(exception_master_id=master_id)
    await state.set_state(MasterScheduleExceptionState.entering_period)
    await callback.message.answer(
        "🏖 Введіть період, який потрібно повністю закрити.\\n\\n"
        "Формат: 29.09.2026-05.10.2026\\n"
        "Обидві дати входять у період."
    )
    await callback.answer()


@router.message(MasterScheduleExceptionState.entering_period)
async def master_exception_period_received(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    raw = (message.text or "").strip().replace("–", "-").replace("—", "-")
    parts = raw.split("-", 1)
    if len(parts) != 2:
        await message.answer("❌ Формат: 29.09.2026-05.10.2026")
        return

    start_date = _parse_admin_date(parts[0])
    end_date = _parse_admin_date(parts[1])
    if not start_date or not end_date or start_date > end_date:
        await message.answer("❌ Перевірте дати. Формат: 29.09.2026-05.10.2026")
        return

    data = await state.get_data()
    master_id = data["exception_master_id"]
    await close_master_schedule_period(
        master_id,
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
    )
    await message.answer(
        f"✅ Період {start_date.strftime('%d.%m.%Y')}–"
        f"{end_date.strftime('%d.%m.%Y')} закрито для онлайн-запису."
    )
    await show_schedule_exceptions_menu(message, master_id, state)


@router.callback_query(F.data.startswith("master_exception_list:"))
async def master_exception_list_handler(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return
    master_id = int(callback.data.split(":", 1)[1])
    master = await get_master_by_id(master_id)
    exceptions = await get_master_schedule_exceptions(master_id)

    if not exceptions:
        await callback.message.answer("📋 Винятків графіка поки немає.")
        await callback.answer()
        return

    lines = [f"📋 Винятки графіка — {master['name']}:", ""]
    for item in exceptions:
        shown = datetime.strptime(item["date"], "%Y-%m-%d").strftime("%d.%m.%Y")
        if item["is_working"]:
            lines.append(f"🟢 {shown}: {item['start_time']}–{item['end_time']}")
        else:
            lines.append(f"🚫 {shown}: закрито")

    result = "\\n".join(lines)
    if len(result) > 3900:
        result = result[:3900] + "\\n…"
    await callback.message.answer(result)
    await callback.answer()


@router.callback_query(F.data.startswith("master_exception_delete:"))
async def master_exception_delete_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return
    master_id = int(callback.data.split(":", 1)[1])
    await state.clear()
    await state.update_data(exception_master_id=master_id)
    await state.set_state(MasterScheduleExceptionState.deleting_date)
    await callback.message.answer(
        "🗑 Введіть дату, для якої потрібно прибрати виняток.\\n\\n"
        "Наприклад: 28.09.2026"
    )
    await callback.answer()


@router.message(MasterScheduleExceptionState.deleting_date)
async def master_exception_delete_received(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    selected = _parse_admin_date(message.text or "")
    if not selected:
        await message.answer("❌ Невірна дата. Приклад: 28.09.2026")
        return

    data = await state.get_data()
    master_id = data["exception_master_id"]
    selected_date = selected.strftime("%Y-%m-%d")
    deleted = await delete_master_schedule_exception(master_id, selected_date)

    await message.answer(
        "✅ Виняток видалено. Знову діє звичайний графік."
        if deleted
        else "ℹ️ Для цієї дати винятку не знайдено."
    )
    await show_schedule_exceptions_menu(message, master_id, state)


@router.message(F.text.startswith("/check_calendar"))
async def check_calendar(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    parts = (message.text or "").strip().split(maxsplit=1)

    if len(parts) != 2:
        await message.answer(
            "🔎 Перевірка календаря Nastya\n\n"
            "Використання:\n"
            "/check_calendar 2026-09-16"
        )
        return

    date_text = parts[1].strip()

    try:
        check_date = datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError:
        await message.answer(
            "❌ Некоректна дата.\n\n"
            "Використовуйте формат:\n"
            "/check_calendar 2026-09-16"
        )
        return

    NASTYA_ID = 7
    timezone = "Europe/Lisbon"

    master = await get_master_by_id(NASTYA_ID)

    if not master:
        await message.answer("❌ Nastya (ID 7) не знайдена в базі.")
        return

    calendar_id = master["calendar_id"]

    if not calendar_id:
        await message.answer("❌ У Nastya не вказаний Google Calendar ID.")
        return

    day_names = {
        0: "Пн",
        1: "Вт",
        2: "Ср",
        3: "Чт",
        4: "Пт",
        5: "Сб",
        6: "Нд",
    }

    day_name = day_names[check_date.weekday()]
    schedule_line = None
    work_start = None
    work_end = None

    for raw_line in (master["schedule"] or "").splitlines():
        line = raw_line.strip()

        if not line.startswith(day_name):
            continue

        schedule_line = line
        lowered = line.lower()

        if "вихідний" in lowered or "folga" in lowered:
            break

        if ":" not in line:
            break

        _, hours = line.split(":", 1)

        if "-" not in hours:
            break

        work_start, work_end = [value.strip() for value in hours.strip().split("-", 1)]
        break

    tz = ZoneInfo(timezone)
    range_start = datetime.combine(
        check_date,
        time.min,
        tzinfo=tz,
    )
    range_end = datetime.combine(
        check_date,
        time.max,
        tzinfo=tz,
    )

    try:
        service = get_calendar_service()

        result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=range_start.isoformat(),
                timeMax=range_end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                showDeleted=False,
                maxResults=250,
            )
            .execute()
        )

        events = result.get("items", [])

    except Exception as error:
        await message.answer(
            "❌ Помилка Google Calendar:\n\n" f"{type(error).__name__}: {error}"
        )
        return

    lines = [
        "🔎 Перевірка календаря Nastya",
        "",
        f"👤 Майстер: {master['name']} (ID {NASTYA_ID})",
        f"📅 Calendar ID: {calendar_id}",
        f"📆 Дата: {check_date.strftime('%d.%m.%Y')} ({day_name})",
        f"🕒 Рядок графіка: {schedule_line or 'не знайдено'}",
    ]

    if work_start and work_end:
        lines.append(f"✅ Робочий час: {work_start}-{work_end}")
    else:
        lines.append("❌ За графіком цей день не є робочим.")

    lines.extend(
        [
            f"📌 Подій Google Calendar: {len(events)}",
            "",
        ]
    )

    if not events:
        lines.append("✅ Google Calendar не містить подій на цю дату.")
    else:
        for index, event in enumerate(events, start=1):
            summary = event.get("summary") or "Без назви"
            status = event.get("status") or "—"
            transparency = event.get("transparency") or "opaque (за замовчуванням)"

            start = event.get("start", {})
            end = event.get("end", {})

            start_value = start.get("dateTime") or start.get("date") or "—"
            end_value = end.get("dateTime") or end.get("date") or "—"

            lines.extend(
                [
                    f"{index}. {summary}",
                    f"START: {start_value}",
                    f"END: {end_value}",
                    f"STATUS: {status}",
                    f"TRANSPARENCY: {transparency}",
                    "➡️ Ця подія блокує свій час у боті.",
                    "",
                ]
            )

    await message.answer("\n".join(lines))
