from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS

from database.queries import (
    get_active_masters,
    add_service,
    get_all_services_admin,
    get_service_by_id,
    update_service,
    deactivate_service,
    get_all_users,
    add_service_extra,
)

from keyboards.menus import admin_menu
from locales.ua import TEXTS as UA_TEXTS, BUTTONS as UA_BUTTONS
from states.admin_state import (
    AddServiceState,
    EditServiceState,
    AddExtraState,
    MailingState,
)

router = Router()

DEFAULT_DEPOSIT_AMOUNT = 10


SERVICE_CATEGORIES = {
    "wm": {
        "ua": "Манікюр жіночий",
        "pt": "Manicure feminina",
    },
    "wp": {
        "ua": "Педикюр жіночий",
        "pt": "Pedicure feminina",
    },
    "ms": {
        "ua": "Чоловічий манікюр та педикюр",
        "pt": "Manicure e pedicure masculina",
    },
    "add": {
        "ua": "Додаткові послуги",
        "pt": "Serviços adicionais",
    },
}


def admin_services_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["add_service"],
                    callback_data="admin_add_service",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✨ Додати додаткову послугу",
                    callback_data="admin_add_extra",
                )
            ],
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["edit_service"],
                    callback_data="admin_edit_service",
                )
            ],
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["delete_service"],
                    callback_data="admin_delete_service",
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


def masters_for_service_keyboard(masters):
    keyboard = []

    for master in masters:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🌸 {master['name']}",
                    callback_data=f"sm:{master['id']}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text=UA_BUTTONS["back"],
                callback_data="back_to_services_menu",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def masters_for_extra_keyboard(masters):
    keyboard = []

    for master in masters:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🌸 {master['name']}",
                    callback_data=f"extra_master:{master['id']}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text=UA_BUTTONS["back"],
                callback_data="back_to_services_menu",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def service_categories_keyboard(prefix: str = "sc"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💅 Манікюр жіночий",
                    callback_data=f"{prefix}:wm",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👣 Педикюр жіночий",
                    callback_data=f"{prefix}:wp",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧔 Чоловічий манікюр та педикюр",
                    callback_data=f"{prefix}:ms",
                )
            ],
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["back"],
                    callback_data="back_to_services_menu",
                )
            ],
        ]
    )


def edit_service_categories_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💅 Манікюр жіночий",
                    callback_data="edit_sc:wm",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👣 Педикюр жіночий",
                    callback_data="edit_sc:wp",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧔 Чоловічий манікюр та педикюр",
                    callback_data="edit_sc:ms",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✨ Додаткові послуги",
                    callback_data="edit_sc:add",
                )
            ],
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["back"],
                    callback_data="back_to_services_menu",
                )
            ],
        ]
    )


def back_to_category_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["back"],
                    callback_data="back_to_service_category",
                )
            ]
        ]
    )


def back_to_name_ua_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["back"],
                    callback_data="back_to_service_name_ua",
                )
            ]
        ]
    )


def back_to_name_pt_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["back"],
                    callback_data="back_to_service_name_pt",
                )
            ]
        ]
    )


def back_to_description_ua_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["back"],
                    callback_data="back_to_service_description_ua",
                )
            ]
        ]
    )


def back_to_description_pt_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["back"],
                    callback_data="back_to_service_description_pt",
                )
            ]
        ]
    )


def back_to_price_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["back"],
                    callback_data="back_to_service_price",
                )
            ]
        ]
    )


def services_choose_keyboard(services, action: str):
    keyboard = []

    for service in services:
        status = "✅" if service["is_active"] else "🚫"

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {service['name_ua']} ({service['master_name']})",
                    callback_data=f"{action}:{service['id']}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="back_to_services_menu",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ===== НОВЕ ЗРУЧНЕ РЕДАГУВАННЯ ПОСЛУГ =====


def edit_service_masters_keyboard(masters):
    keyboard = []

    for master in masters:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🌸 {master['name']}",
                    callback_data=f"edit_service_master:{master['id']}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="back_to_services_menu",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def edit_services_for_master_keyboard(services):
    keyboard = []

    for service in services:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"💅 {service['name_ua']}",
                    callback_data=f"edit_service:{service['id']}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ До майстрів",
                callback_data="admin_edit_service",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def edit_service_fields_keyboard(service_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📂 Категорія",
                    callback_data=f"edit_field:category:{service_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🇺🇦 Назва UA",
                    callback_data=f"edit_field:name_ua:{service_id}",
                ),
                InlineKeyboardButton(
                    text="🇵🇹 Назва PT",
                    callback_data=f"edit_field:name_pt:{service_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📝 Опис UA",
                    callback_data=f"edit_field:description_ua:{service_id}",
                ),
                InlineKeyboardButton(
                    text="📝 Опис PT",
                    callback_data=f"edit_field:description_pt:{service_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💶 Ціна",
                    callback_data=f"edit_field:price:{service_id}",
                ),
                InlineKeyboardButton(
                    text="⏳ Тривалість",
                    callback_data=f"edit_field:duration:{service_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Видалити послугу",
                    callback_data=f"delete_service:{service_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ До вибору майстра",
                    callback_data="admin_edit_service",
                )
            ],
        ]
    )


async def update_one_service_field(
    service_id: int,
    field: str,
    value,
):
    service = await get_service_by_id(service_id)

    if not service:
        return False

    values = {
        "category_ua": service["category_ua"],
        "category_pt": service["category_pt"],
        "name_ua": service["name_ua"],
        "name_pt": service["name_pt"],
        "description_ua": service["description_ua"],
        "description_pt": service["description_pt"],
        "price": service["price"],
        "duration": service["duration"],
    }

    values[field] = value

    deposit_amount = service["deposit_amount"]
    if deposit_amount is None:
        deposit_amount = DEFAULT_DEPOSIT_AMOUNT

    await update_service(
        service_id=service_id,
        category_ua=values["category_ua"],
        category_pt=values["category_pt"],
        name_ua=values["name_ua"],
        name_pt=values["name_pt"],
        description_ua=values["description_ua"],
        description_pt=values["description_pt"],
        price=values["price"],
        duration=values["duration"],
        deposit_amount=deposit_amount,
    )

    return True


async def send_service_edit_menu(message: Message, service_id: int):
    service = await get_service_by_id(service_id)

    if not service:
        await message.answer("Послугу не знайдено.")
        return

    await message.answer(
        "✏️ Редагування послуги\n\n"
        f"💅 {service['name_ua']}\n"
        f"📂 {service['category_ua']}\n"
        f"💶 {service['price']} €\n"
        f"⏳ {service['duration']} хв\n\n"
        "Що саме потрібно змінити?",
        reply_markup=edit_service_fields_keyboard(service_id),
    )


@router.message(Command("admin"))
async def admin_panel(message: Message):
    print("ADMIN COMMAND FROM:", message.from_user.id)

    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас немає доступу до адмін-панелі.")
        return

    await message.answer(
        UA_TEXTS["admin_panel"],
        reply_markup=admin_menu(),
    )


@router.message(F.text == UA_BUTTONS["admin_services"])
async def admin_services_menu(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас немає доступу.")
        return

    await message.answer(
        "💅 Управління послугами\n\nОберіть дію:",
        reply_markup=admin_services_keyboard(),
    )


@router.callback_query(F.data == "admin_add_service")
async def start_add_service(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    masters = await get_active_masters()

    if not masters:
        await callback.message.answer(
            "Спочатку потрібно додати хоча б одного майстра 👩"
        )
        await callback.answer()
        return

    await state.clear()
    await state.set_state(AddServiceState.master)

    await callback.message.answer(
        "💅 Додавання послуги\n\n" "Оберіть майстра, до якого буде прив’язана послуга:",
        reply_markup=masters_for_service_keyboard(masters),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("sm:"))
async def choose_master_for_service(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    master_id = int(callback.data.split(":")[1])

    await state.update_data(master_id=master_id)
    await state.set_state(AddServiceState.category)

    await callback.message.answer(
        "Оберіть категорію послуги:",
        reply_markup=service_categories_keyboard(),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("sc:"))
async def choose_service_category(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    category_key = callback.data.split(":")[1]
    category = SERVICE_CATEGORIES.get(category_key)

    if not category:
        await callback.answer("Категорію не знайдено", show_alert=True)
        return

    await state.update_data(
        category_ua=category["ua"],
        category_pt=category["pt"],
    )

    await state.set_state(AddServiceState.name_ua)

    await callback.message.answer(
        "🇺🇦 Введіть назву послуги українською:\n\n" "Наприклад: Манікюр + гель-лак",
        reply_markup=back_to_category_keyboard(),
    )

    await callback.answer()


@router.message(AddServiceState.name_ua)
async def add_service_name_ua(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    await state.update_data(name_ua=message.text)
    await state.set_state(AddServiceState.name_pt)

    await message.answer(
        "🇵🇹 Введіть назву послуги португальською:\n\n"
        "Наприклад: Manicure com gelinho",
        reply_markup=back_to_name_ua_keyboard(),
    )


@router.message(AddServiceState.name_pt)
async def add_service_name_pt(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    await state.update_data(name_pt=message.text)
    await state.set_state(AddServiceState.description_ua)

    await message.answer(
        "🇺🇦 Введіть опис послуги українською:",
        reply_markup=back_to_name_pt_keyboard(),
    )


@router.message(AddServiceState.description_ua)
async def add_service_description_ua(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    await state.update_data(description_ua=message.text)
    await state.set_state(AddServiceState.description_pt)

    await message.answer(
        "🇵🇹 Введіть опис послуги португальською:",
        reply_markup=back_to_description_ua_keyboard(),
    )


@router.message(AddServiceState.description_pt)
async def add_service_description_pt(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    await state.update_data(description_pt=message.text)
    await state.set_state(AddServiceState.price)

    await message.answer(
        "💶 Введіть ціну послуги в євро:\n\nНаприклад: 50",
        reply_markup=back_to_description_pt_keyboard(),
    )


@router.message(AddServiceState.price)
async def add_service_price(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer(
            "Введіть ціну числом. Наприклад: 50",
            reply_markup=back_to_description_pt_keyboard(),
        )
        return

    await state.update_data(price=price)
    await state.set_state(AddServiceState.duration)

    await message.answer(
        "⏳ Введіть тривалість послуги в хвилинах:\n\nНаприклад: 90",
        reply_markup=back_to_price_keyboard(),
    )


@router.message(AddServiceState.duration)
async def add_service_duration(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        duration = int(message.text)
    except ValueError:
        await message.answer("Введіть тривалість числом. Наприклад: 90")
        return

    await state.update_data(duration=duration)

    data = await state.get_data()

    await add_service(
        master_id=data["master_id"],
        category_ua=data["category_ua"],
        category_pt=data["category_pt"],
        name_ua=data["name_ua"],
        name_pt=data["name_pt"],
        description_ua=data["description_ua"],
        description_pt=data["description_pt"],
        price=data["price"],
        duration=data["duration"],
        deposit_amount=DEFAULT_DEPOSIT_AMOUNT,
    )

    await state.clear()

    await message.answer(
        "✅ Послугу успішно додано!\n\n"
        f"Категорія: {data['category_ua']}\n"
        f"Назва: {data['name_ua']}\n"
        f"Ціна: {data['price']}€\n"
        f"Тривалість: {data['duration']} хв\n"
        f"Завдаток: {DEFAULT_DEPOSIT_AMOUNT}€",
        reply_markup=admin_menu(),
    )


@router.callback_query(F.data == "back_to_services_menu")
async def back_to_services_menu(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    await state.clear()

    await callback.message.answer(
        "💅 Управління послугами\n\nОберіть дію:",
        reply_markup=admin_services_keyboard(),
    )

    await callback.answer()


@router.callback_query(F.data == "back_to_service_master_choice")
async def back_to_service_master_choice(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    masters = await get_active_masters()

    await state.set_state(AddServiceState.master)

    await callback.message.answer(
        "💅 Додавання послуги\n\n" "Оберіть майстра, до якого буде прив’язана послуга:",
        reply_markup=masters_for_service_keyboard(masters),
    )

    await callback.answer()


@router.callback_query(F.data == "back_to_service_category")
async def back_to_service_category(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    await state.set_state(AddServiceState.category)

    await callback.message.answer(
        "Оберіть категорію послуги:",
        reply_markup=service_categories_keyboard(),
    )

    await callback.answer()


@router.callback_query(F.data == "back_to_service_name_ua")
async def back_to_service_name_ua(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    await state.set_state(AddServiceState.name_ua)

    await callback.message.answer(
        "🇺🇦 Введіть назву послуги українською:\n\n" "Наприклад: Манікюр + гель-лак",
        reply_markup=back_to_category_keyboard(),
    )

    await callback.answer()


@router.callback_query(F.data == "back_to_service_name_pt")
async def back_to_service_name_pt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    await state.set_state(AddServiceState.name_pt)

    await callback.message.answer(
        "🇵🇹 Введіть назву послуги португальською:\n\n"
        "Наприклад: Manicure com gelinho",
        reply_markup=back_to_name_ua_keyboard(),
    )

    await callback.answer()


@router.callback_query(F.data == "back_to_service_description_ua")
async def back_to_service_description_ua(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    await state.set_state(AddServiceState.description_ua)

    await callback.message.answer(
        "🇺🇦 Введіть опис послуги українською:",
        reply_markup=back_to_name_pt_keyboard(),
    )

    await callback.answer()


@router.callback_query(F.data == "back_to_service_description_pt")
async def back_to_service_description_pt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    await state.set_state(AddServiceState.description_pt)

    await callback.message.answer(
        "🇵🇹 Введіть опис послуги португальською:",
        reply_markup=back_to_description_ua_keyboard(),
    )

    await callback.answer()


@router.callback_query(F.data == "back_to_service_price")
async def back_to_service_price(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    await state.set_state(AddServiceState.price)

    await callback.message.answer(
        "💶 Введіть ціну послуги в євро:\n\nНаприклад: 50",
        reply_markup=back_to_description_pt_keyboard(),
    )

    await callback.answer()


# ===== РЕДАГУВАННЯ ПОСЛУГ: МАЙСТЕР → ПОСЛУГА → ПОЛЕ =====


@router.callback_query(F.data == "admin_edit_service")
async def choose_service_to_edit(
    callback: CallbackQuery,
    state: FSMContext,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    await state.clear()

    masters = await get_active_masters()

    if not masters:
        await callback.message.answer("Поки що немає активних майстрів.")
        await callback.answer()
        return

    await callback.message.answer(
        "✏️ Редагування послуги\n\nСпочатку оберіть майстра:",
        reply_markup=edit_service_masters_keyboard(masters),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("edit_service_master:"))
async def choose_master_for_service_edit(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    master_id = int(callback.data.split(":")[1])

    all_services = await get_all_services_admin()
    services = [
        service for service in all_services if service["master_id"] == master_id
    ]

    if not services:
        await callback.message.answer(
            "У цього майстра поки немає послуг.",
            reply_markup=edit_service_masters_keyboard(await get_active_masters()),
        )
        await callback.answer()
        return

    await callback.message.answer(
        "💅 Оберіть послугу:",
        reply_markup=edit_services_for_master_keyboard(services),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("edit_service:"))
async def start_edit_service(
    callback: CallbackQuery,
    state: FSMContext,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    service_id = int(callback.data.split(":")[1])
    service = await get_service_by_id(service_id)

    if not service:
        await callback.answer("Послугу не знайдено", show_alert=True)
        return

    await state.clear()
    await state.update_data(service_id=service_id)
    await state.set_state(EditServiceState.service)

    await send_service_edit_menu(callback.message, service_id)
    await callback.answer()


@router.callback_query(F.data.startswith("edit_field:"))
async def choose_service_field(
    callback: CallbackQuery,
    state: FSMContext,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    _, field, service_id_raw = callback.data.split(":")
    service_id = int(service_id_raw)

    service = await get_service_by_id(service_id)

    if not service:
        await callback.answer("Послугу не знайдено", show_alert=True)
        return

    await state.clear()
    await state.update_data(service_id=service_id)

    if field == "category":
        await state.set_state(EditServiceState.category)
        await callback.message.answer(
            "📂 Поточна категорія:\n"
            f"{service['category_ua']}\n\n"
            "Оберіть нову категорію:",
            reply_markup=edit_service_categories_keyboard(),
        )

    elif field == "name_ua":
        await state.set_state(EditServiceState.name_ua)
        await callback.message.answer(
            "🇺🇦 Поточна назва:\n" f"{service['name_ua']}\n\n" "Введіть нову назву:"
        )

    elif field == "name_pt":
        await state.set_state(EditServiceState.name_pt)
        await callback.message.answer(
            "🇵🇹 Поточна назва:\n" f"{service['name_pt']}\n\n" "Введіть нову назву:"
        )

    elif field == "description_ua":
        await state.set_state(EditServiceState.description_ua)
        await callback.message.answer(
            "🇺🇦 Поточний опис:\n"
            f"{service['description_ua']}\n\n"
            "Введіть новий опис:"
        )

    elif field == "description_pt":
        await state.set_state(EditServiceState.description_pt)
        await callback.message.answer(
            "🇵🇹 Поточний опис:\n"
            f"{service['description_pt']}\n\n"
            "Введіть новий опис:"
        )

    elif field == "price":
        await state.set_state(EditServiceState.price)
        await callback.message.answer(
            f"💶 Поточна ціна: {service['price']} €\n\n" "Введіть нову ціну:"
        )

    elif field == "duration":
        await state.set_state(EditServiceState.duration)
        await callback.message.answer(
            "⏳ Поточна тривалість: "
            f"{service['duration']} хв\n\n"
            "Введіть нову тривалість у хвилинах:"
        )

    await callback.answer()


@router.callback_query(F.data.startswith("edit_sc:"))
async def edit_service_category(
    callback: CallbackQuery,
    state: FSMContext,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    data = await state.get_data()
    service_id = data.get("service_id")

    if not service_id:
        await callback.answer(
            "Сесію редагування втрачено.",
            show_alert=True,
        )
        return

    category_key = callback.data.split(":")[1]
    category = SERVICE_CATEGORIES.get(category_key)

    if not category:
        await callback.answer("Категорію не знайдено", show_alert=True)
        return

    service = await get_service_by_id(service_id)

    if not service:
        await callback.answer("Послугу не знайдено", show_alert=True)
        return

    deposit_amount = service["deposit_amount"]
    if deposit_amount is None:
        deposit_amount = DEFAULT_DEPOSIT_AMOUNT

    await update_service(
        service_id=service_id,
        category_ua=category["ua"],
        category_pt=category["pt"],
        name_ua=service["name_ua"],
        name_pt=service["name_pt"],
        description_ua=service["description_ua"],
        description_pt=service["description_pt"],
        price=service["price"],
        duration=service["duration"],
        deposit_amount=deposit_amount,
    )

    await state.clear()

    await callback.message.answer("✅ Категорію змінено.")
    await send_service_edit_menu(callback.message, service_id)
    await callback.answer()


@router.message(EditServiceState.name_ua)
async def edit_service_name_ua(
    message: Message,
    state: FSMContext,
):
    if message.from_user.id not in ADMIN_IDS:
        return

    data = await state.get_data()
    service_id = data.get("service_id")

    if not service_id:
        await message.answer("Сесію редагування втрачено.")
        await state.clear()
        return

    await update_one_service_field(
        service_id,
        "name_ua",
        message.text,
    )

    await state.clear()

    await message.answer("✅ Назву українською змінено.")
    await send_service_edit_menu(message, service_id)


@router.message(EditServiceState.name_pt)
async def edit_service_name_pt(
    message: Message,
    state: FSMContext,
):
    if message.from_user.id not in ADMIN_IDS:
        return

    data = await state.get_data()
    service_id = data.get("service_id")

    if not service_id:
        await message.answer("Сесію редагування втрачено.")
        await state.clear()
        return

    await update_one_service_field(
        service_id,
        "name_pt",
        message.text,
    )

    await state.clear()

    await message.answer("✅ Назву португальською змінено.")
    await send_service_edit_menu(message, service_id)


@router.message(EditServiceState.description_ua)
async def edit_service_description_ua(
    message: Message,
    state: FSMContext,
):
    if message.from_user.id not in ADMIN_IDS:
        return

    data = await state.get_data()
    service_id = data.get("service_id")

    if not service_id:
        await message.answer("Сесію редагування втрачено.")
        await state.clear()
        return

    await update_one_service_field(
        service_id,
        "description_ua",
        message.text,
    )

    await state.clear()

    await message.answer("✅ Опис українською змінено.")
    await send_service_edit_menu(message, service_id)


@router.message(EditServiceState.description_pt)
async def edit_service_description_pt(
    message: Message,
    state: FSMContext,
):
    if message.from_user.id not in ADMIN_IDS:
        return

    data = await state.get_data()
    service_id = data.get("service_id")

    if not service_id:
        await message.answer("Сесію редагування втрачено.")
        await state.clear()
        return

    await update_one_service_field(
        service_id,
        "description_pt",
        message.text,
    )

    await state.clear()

    await message.answer("✅ Опис португальською змінено.")
    await send_service_edit_menu(message, service_id)


@router.message(EditServiceState.price)
async def edit_service_price(
    message: Message,
    state: FSMContext,
):
    if message.from_user.id not in ADMIN_IDS:
        return

    data = await state.get_data()
    service_id = data.get("service_id")

    if not service_id:
        await message.answer("Сесію редагування втрачено.")
        await state.clear()
        return

    try:
        price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введіть ціну числом. Наприклад: 45")
        return

    await update_one_service_field(
        service_id,
        "price",
        price,
    )

    await state.clear()

    await message.answer("✅ Ціну змінено.")
    await send_service_edit_menu(message, service_id)


@router.message(EditServiceState.duration)
async def edit_service_duration(
    message: Message,
    state: FSMContext,
):
    if message.from_user.id not in ADMIN_IDS:
        return

    data = await state.get_data()
    service_id = data.get("service_id")

    if not service_id:
        await message.answer("Сесію редагування втрачено.")
        await state.clear()
        return

    try:
        duration = int(message.text)
    except ValueError:
        await message.answer("Введіть тривалість числом у хвилинах. Наприклад: 90")
        return

    await update_one_service_field(
        service_id,
        "duration",
        duration,
    )

    await state.clear()

    await message.answer("✅ Тривалість змінено.")
    await send_service_edit_menu(message, service_id)


# ===== ВИДАЛЕННЯ / ВИМКНЕННЯ ПОСЛУГ =====


@router.callback_query(F.data == "admin_delete_service")
async def choose_service_to_delete(callback: CallbackQuery):
    services = await get_all_services_admin()

    if not services:
        await callback.message.answer("Поки що немає послуг.")
        await callback.answer()
        return

    await callback.message.answer(
        "❌ Оберіть послугу для вимкнення:",
        reply_markup=services_choose_keyboard(
            services,
            "delete_service",
        ),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("delete_service:"))
async def delete_service_handler(callback: CallbackQuery):
    service_id = int(callback.data.split(":")[1])

    await deactivate_service(service_id)

    await callback.message.answer(
        "🚫 Послугу вимкнено.\n\n" "Вона більше не буде показуватись клієнтам.",
        reply_markup=admin_menu(),
    )

    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    await state.clear()

    await callback.message.answer(
        UA_TEXTS["admin_panel"],
        reply_markup=admin_menu(),
    )

    await callback.answer()


def mailing_confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Надіслати всім",
                    callback_data="mailing_confirm_send",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Скасувати",
                    callback_data="mailing_cancel",
                )
            ],
        ]
    )


def extra_service_categories_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💅 Манікюр жіночий",
                    callback_data="extra_sc:wm",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👣 Педикюр жіночий",
                    callback_data="extra_sc:wp",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧔 Чоловічий манікюр та педикюр",
                    callback_data="extra_sc:ms",
                )
            ],
            [
                InlineKeyboardButton(
                    text=UA_BUTTONS["back"],
                    callback_data="back_to_services_menu",
                )
            ],
        ]
    )


@router.message(F.text == UA_BUTTONS["admin_mailing"])
async def admin_mailing_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас немає доступу.")
        return

    await state.clear()
    await state.set_state(MailingState.text)

    await message.answer(
        "📢 Розсилка\n\n"
        "Надішліть текст або фото.\n\n"
        "Якщо надсилаєте фото — текст можна додати як підпис до фото."
    )


@router.message(MailingState.text)
async def admin_mailing_get_content(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    if message.photo:
        photo_id = message.photo[-1].file_id
        caption = message.caption or ""

        await state.update_data(
            type="photo",
            photo_id=photo_id,
            text=caption,
        )

        await message.answer_photo(
            photo=photo_id,
            caption=caption or "Без тексту",
            reply_markup=mailing_confirm_keyboard(),
        )

    elif message.text:
        await state.update_data(
            type="text",
            text=message.text,
        )

        await message.answer(
            "📢 Превʼю розсилки:\n\n" f"{message.text}",
            reply_markup=mailing_confirm_keyboard(),
        )

    else:
        await message.answer("Надішліть текст або фото.")
        return

    await state.set_state(MailingState.confirm)


@router.callback_query(F.data == "mailing_confirm_send")
async def admin_mailing_send(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    data = await state.get_data()
    users = await get_all_users()

    sent = 0
    failed = 0

    for user in users:
        try:
            telegram_id = user["telegram_id"]

            if data["type"] == "photo":
                await callback.bot.send_photo(
                    chat_id=telegram_id,
                    photo=data["photo_id"],
                    caption=data.get("text") or None,
                )
            else:
                await callback.bot.send_message(
                    chat_id=telegram_id,
                    text=data["text"],
                )

            sent += 1

        except Exception:
            failed += 1

    await state.clear()

    await callback.message.answer(
        "✅ Розсилку завершено\n\n" f"📨 Відправлено: {sent}\n" f"⚠️ Помилки: {failed}",
        reply_markup=admin_menu(),
    )

    await callback.answer()


@router.callback_query(F.data == "mailing_cancel")
async def admin_mailing_cancel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    await state.clear()

    await callback.message.answer(
        "❌ Розсилку скасовано.",
        reply_markup=admin_menu(),
    )

    await callback.answer()


@router.callback_query(F.data == "admin_add_extra")
async def start_add_extra(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Немає доступу", show_alert=True)
        return

    masters = await get_active_masters()

    if not masters:
        await callback.message.answer("Спочатку додайте хоча б одного майстра.")
        await callback.answer()
        return

    await state.clear()
    await state.set_state(AddExtraState.master)

    await callback.message.answer(
        "✨ Додавання додаткової послуги\n\nОберіть майстра:",
        reply_markup=masters_for_extra_keyboard(masters),
    )

    await callback.answer()


@router.callback_query(
    AddExtraState.master,
    F.data.startswith("extra_master:"),
)
async def choose_master_for_extra(
    callback: CallbackQuery,
    state: FSMContext,
):
    master_id = int(callback.data.split(":")[1])

    await state.update_data(master_id=master_id)
    await state.set_state(AddExtraState.category)

    await callback.message.answer(
        "Оберіть категорію, до якої буде додаткова послуга:",
        reply_markup=extra_service_categories_keyboard(),
    )

    await callback.answer()


@router.callback_query(
    AddExtraState.category,
    F.data.startswith("extra_sc:"),
)
async def choose_extra_category(
    callback: CallbackQuery,
    state: FSMContext,
):
    category_key = callback.data.split(":")[1]
    category = SERVICE_CATEGORIES.get(category_key)

    if not category:
        await callback.answer(
            "Категорію не знайдено",
            show_alert=True,
        )
        return

    await state.update_data(
        category_ua=category["ua"],
        category_pt=category["pt"],
    )

    await state.set_state(AddExtraState.name_ua)

    await callback.message.answer("🇺🇦 Введіть назву додаткової послуги:")
    await callback.answer()


@router.message(AddExtraState.name_ua)
async def add_extra_name_ua(message: Message, state: FSMContext):
    await state.update_data(name_ua=message.text)
    await state.set_state(AddExtraState.name_pt)

    await message.answer("🇵🇹 Введіть назву португальською:")


@router.message(AddExtraState.name_pt)
async def add_extra_name_pt(message: Message, state: FSMContext):
    await state.update_data(name_pt=message.text)
    await state.set_state(AddExtraState.price)

    await message.answer("💶 Введіть ціну додаткової послуги:")


@router.message(AddExtraState.price)
async def add_extra_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введіть ціну числом. Наприклад: 10")
        return

    await state.update_data(price=price)
    await state.set_state(AddExtraState.duration)

    await message.answer("⏳ Введіть тривалість у хвилинах:")


@router.message(AddExtraState.duration)
async def add_extra_duration(message: Message, state: FSMContext):
    try:
        duration = int(message.text)
    except ValueError:
        await message.answer("Введіть тривалість числом. Наприклад: 15")
        return

    await state.update_data(duration=duration)
    data = await state.get_data()

    await add_service_extra(
        master_id=data["master_id"],
        category_ua=data["category_ua"],
        category_pt=data["category_pt"],
        name_ua=data["name_ua"],
        name_pt=data["name_pt"],
        price=data["price"],
        duration=data["duration"],
    )

    await state.clear()

    await message.answer(
        "✅ Додаткову послугу додано!",
        reply_markup=admin_menu(),
    )
