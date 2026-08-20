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


@router.callback_query(F.data == "admin_edit_master")
async def choose_master_to_edit(
    callback: CallbackQuery,
):
    masters = await get_all_masters()

    if not masters:
        await callback.message.answer("Поки що немає майстрів для редагування.")

        await callback.answer()
        return

    await callback.message.answer(
        "✏️ Оберіть майстра для редагування:",
        reply_markup=masters_choose_keyboard(
            masters,
            "edit_master",
        ),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("edit_master:"))
async def start_edit_master(
    callback: CallbackQuery,
    state: FSMContext,
):
    master_id = int(callback.data.split(":")[1])

    master = await get_master_by_id(master_id)

    if not master:
        await callback.answer(
            "Майстра не знайдено",
            show_alert=True,
        )
        return

    await state.clear()

    await state.update_data(
        master_id=master_id,
    )

    await state.set_state(
        EditMasterState.name,
    )

    await callback.message.answer(
        "✏️ Редагування майстра\n\n"
        f"Поточне ім’я: {master['name']}\n\n"
        "Введіть нове ім’я "
        "або напишіть: залишити"
    )

    await callback.answer()


@router.message(EditMasterState.name)
async def edit_master_name(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    master = await get_master_by_id(data["master_id"])

    name = master["name"] if message.text.lower() == "залишити" else message.text

    await state.update_data(
        name=name,
    )

    await state.set_state(
        EditMasterState.photo,
    )

    await message.answer(
        "📸 Надішліть нове фото.\n\n"
        "Або напишіть:\n"
        "залишити — залишити старе фото\n"
        "пропустити — прибрати фото"
    )


@router.message(EditMasterState.photo)
async def edit_master_photo(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    master = await get_master_by_id(data["master_id"])

    if message.photo:
        photo_id = message.photo[-1].file_id

    elif message.text and message.text.lower() == "залишити":
        photo_id = master["photo_id"]

    elif message.text and message.text.lower() in ["пропустити", "skip"]:
        photo_id = None

    else:
        await message.answer("Надішліть фото або напишіть: " "залишити / пропустити")
        return

    await state.update_data(
        photo_id=photo_id,
    )

    await state.set_state(
        EditMasterState.description_ua,
    )

    await message.answer("🇺🇦 Введіть новий опис українською " "або напишіть: залишити")


@router.message(EditMasterState.description_ua)
async def edit_master_description_ua(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    master = await get_master_by_id(data["master_id"])

    description_ua = (
        master["description_ua"] if message.text.lower() == "залишити" else message.text
    )

    await state.update_data(
        description_ua=description_ua,
    )

    await state.set_state(
        EditMasterState.description_pt,
    )

    await message.answer(
        "🇵🇹 Введіть новий опис португальською " "або напишіть: залишити"
    )


@router.message(EditMasterState.description_pt)
async def edit_master_description_pt(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    master = await get_master_by_id(data["master_id"])

    description_pt = (
        master["description_pt"] if message.text.lower() == "залишити" else message.text
    )

    await state.update_data(
        description_pt=description_pt,
    )

    await state.set_state(
        EditMasterState.telegram_id,
    )

    await message.answer(
        "🆔 Введіть новий Telegram ID.\n\n"
        "Або напишіть:\n"
        "залишити — залишити старий ID\n"
        "пропустити — прибрати ID"
    )


@router.message(EditMasterState.telegram_id)
async def edit_master_telegram_id(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    master = await get_master_by_id(data["master_id"])

    if message.text.lower() == "залишити":
        telegram_id = master["telegram_id"]

    elif message.text.lower() in [
        "пропустити",
        "skip",
    ]:
        telegram_id = None

    else:
        try:
            telegram_id = int(message.text)

        except ValueError:
            await message.answer(
                "Telegram ID має бути числом " "або напишіть: " "залишити / пропустити"
            )
            return

    await state.update_data(
        telegram_id=telegram_id,
    )

    await state.set_state(
        EditMasterState.schedule,
    )

    await message.answer(
        "🕒 Введіть графік роботи.\n\n"
        "Приклад:\n"
        "Пн: 08:30-18:30\n"
        "Вт: 08:30-18:30\n"
        "Ср: 08:30-18:30\n"
        "Чт: 08:30-18:30\n"
        "Пт: 08:30-18:30\n"
        "Сб: вихідний\n"
        "Нд: вихідний\n\n"
        "Або напишіть: залишити"
    )


@router.message(EditMasterState.schedule)
async def edit_master_schedule(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    master = await get_master_by_id(data["master_id"])

    schedule = (
        master["schedule"] if message.text.lower() == "залишити" else message.text
    )

    await state.update_data(
        schedule=schedule,
    )

    await state.set_state(
        EditMasterState.calendar_id,
    )

    await message.answer(
        "📅 Введіть новий Google Calendar ID.\n\n"
        f"Поточний Calendar ID:\n"
        f"{master['calendar_id'] or 'Не вказано'}\n\n"
        "Або напишіть:\n"
        "залишити — залишити поточний Calendar ID\n"
        "пропустити — прибрати Calendar ID"
    )


@router.message(EditMasterState.calendar_id)
async def edit_master_calendar_id(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    master = await get_master_by_id(data["master_id"])

    text = message.text.strip()

    if text.lower() == "залишити":
        calendar_id = master["calendar_id"]

    elif text.lower() in [
        "пропустити",
        "skip",
    ]:
        calendar_id = None

    else:
        calendar_id = text

    await update_master(
        master_id=data["master_id"],
        name=data["name"],
        telegram_id=data["telegram_id"],
        photo_id=data["photo_id"],
        description_ua=data["description_ua"],
        description_pt=data["description_pt"],
        schedule=data["schedule"],
        calendar_id=calendar_id,
    )

    await state.clear()

    await message.answer(
        "✅ Дані майстра оновлено!\n\n"
        f"📅 Calendar ID: "
        f"{calendar_id or 'Не вказано'}",
        reply_markup=admin_menu(),
    )


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


@router.message(F.text == "/check_nastya_28")
async def check_nastya_28(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    calendar_id = "nastyazaitseva73@gmail.com"
    timezone = "Europe/Lisbon"

    tz = ZoneInfo(timezone)
    check_date = datetime.strptime(
        "2026-08-28",
        "%Y-%m-%d",
    ).date()

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
        f"📅 Calendar ID: {calendar_id}",
        "📆 Дата: 28.08.2026",
        f"📌 Знайдено подій: {len(events)}",
        "",
    ]

    if not events:
        lines.append("❌ Google API не бачить жодної події на цю дату.")

    else:
        for index, event in enumerate(events, start=1):
            summary = event.get("summary") or "Без назви"

            start = event.get("start", {})
            end = event.get("end", {})

            start_value = start.get("dateTime") or start.get("date") or "—"

            end_value = end.get("dateTime") or end.get("date") or "—"

            lines.extend(
                [
                    f"{index}. {summary}",
                    f"START: {start_value}",
                    f"END: {end_value}",
                    "",
                ]
            )

    await message.answer("\n".join(lines))
