from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from services.calendar import is_time_free

from database.queries import (
    get_user_by_telegram_id,
    accept_rules,
    get_active_masters,
    get_master_by_id,
    get_services_by_master,
    get_service_by_id,
    create_booking,
    add_booking_service,
    update_booking_status,
    update_payment_status,
    get_service_categories_by_master,
    get_services_by_master_and_category,
    get_busy_bookings_by_master_and_date,
    get_service_extras,
    get_service_extras_by_category,
    get_bookings_with_resource_by_date,
    get_extra_by_id,
)

from services.notifications import notify_master_about_booking

from keyboards.inline import (
    booking_rules_keyboard,
    booking_confirm_keyboard,
    deposit_keyboard,
    add_another_service_keyboard,
)
from keyboards.menus import main_menu
from locales.ua import TEXTS as UA_TEXTS, BUTTONS as UA_BUTTONS
from locales.pt import TEXTS as PT_TEXTS, BUTTONS as PT_BUTTONS
from states.booking_state import BookingState

router = Router()

PAYMENT_DETAILS = "IBAN / MBWay / реквізити клієнтки будуть тут"
SALON_ADDRESS = "Cascais"


async def get_user_language(telegram_id: int) -> str:
    user = await get_user_by_telegram_id(telegram_id)

    if user and user["language"]:
        return user["language"]

    return "ua"


def get_texts_and_buttons(language: str):
    if language == "pt":
        return PT_TEXTS, PT_BUTTONS

    return UA_TEXTS, UA_BUTTONS


async def is_user_blocked(telegram_id: int) -> bool:
    user = await get_user_by_telegram_id(telegram_id)
    return bool(user and user["is_blocked"])


async def send_blocked_message(message: Message):
    await message.answer(
        "⛔ Запис через бота для вас недоступний.\n\n"
        "Будь ласка, зв’яжіться з майстром напряму."
    )


async def stop_blocked_callback(callback: CallbackQuery) -> bool:
    if await is_user_blocked(callback.from_user.id):
        await callback.message.answer(
            "⛔ Запис через бота для вас недоступний.\n\n"
            "Будь ласка, зв’яжіться з майстром напряму."
        )
        await callback.answer()
        return True

    return False


async def stop_blocked_message(message: Message) -> bool:
    if await is_user_blocked(message.from_user.id):
        await send_blocked_message(message)
        return True

    return False


def masters_keyboard(masters, language: str = "ua"):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS
    keyboard = []

    for master in masters:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🌸 {master['name']}",
                    callback_data=f"select_master:{master['id']}",
                )
            ]
        )

    keyboard.append(
        [InlineKeyboardButton(text=buttons["back"], callback_data="back_main")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def service_categories_keyboard(categories, language: str = "ua"):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS
    keyboard = []

    for index, category in enumerate(categories):
        category_name = (
            category["category_pt"]
            if language == "pt" and category["category_pt"]
            else category["category_ua"]
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"💅 {category_name}",
                    callback_data=f"select_category:{index}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text=buttons["back"],
                callback_data="back_to_masters",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def services_keyboard(services, language: str = "ua"):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS
    keyboard = []

    for service in services:
        name = (
            service["name_pt"]
            if language == "pt" and service["name_pt"]
            else service["name_ua"]
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"💅 {name} — {service['price']}€",
                    callback_data=f"select_service:{service['id']}",
                )
            ]
        )

    keyboard.append(
        [InlineKeyboardButton(text=buttons["back"], callback_data="back_to_categories")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def extras_keyboard(extras, selected_extras=None, language: str = "ua"):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS

    if selected_extras is None:
        selected_extras = []

    keyboard = []

    for extra in extras:
        extra_id = extra["id"]

        name = (
            extra["name_pt"]
            if language == "pt" and extra["name_pt"]
            else extra["name_ua"]
        )

        mark = "✅" if extra_id in selected_extras else "➕"

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {name} — {extra['price']}€",
                    callback_data=f"toggle_extra:{extra_id}",
                )
            ]
        )

    skip_text = "Sem adicionais" if language == "pt" else "Без додаткових послуг"

    keyboard.append([InlineKeyboardButton(text=skip_text, callback_data="extras_skip")])

    keyboard.append(
        [InlineKeyboardButton(text=buttons["back"], callback_data="back_to_services")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def dates_keyboard(language: str = "ua"):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS
    keyboard = []

    today = datetime.now()

    for i in range(30):
        date = today + timedelta(days=i)
        date_text = date.strftime("%d.%m.%Y")
        callback_date = date.strftime("%Y-%m-%d")

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=date_text,
                    callback_data=f"select_date:{callback_date}",
                )
            ]
        )

    keyboard.append(
        [InlineKeyboardButton(text=buttons["back"], callback_data="back_to_services")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


DAY_NAMES_UA = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Нд",
}


def get_work_hours_for_date(schedule: str, selected_date: str):
    if not schedule:
        return None, None

    selected_weekday = datetime.strptime(selected_date, "%Y-%m-%d").weekday()
    day_name = DAY_NAMES_UA[selected_weekday]

    for line in schedule.splitlines():
        line = line.strip()

        if not line:
            continue

        if not line.startswith(day_name):
            continue

        if "вихідний" in line.lower():
            return None, None

        if ":" not in line:
            continue

        _, hours = line.split(":", 1)
        hours = hours.strip()

        if "-" not in hours:
            continue

        work_start, work_end = hours.split("-", 1)

        return work_start.strip(), work_end.strip()

    return None, None


def generate_time_slots(
    work_start: str,
    work_end: str,
    duration: int = 60,
    step: int = 30,
):
    slots = []

    start = datetime.strptime(work_start, "%H:%M")
    end = datetime.strptime(work_end, "%H:%M")

    current = start

    while current <= end:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=step)

    return slots


def times_overlap(start_1, end_1, start_2, end_2):
    return start_1 < end_2 and start_2 < end_1


async def times_keyboard(
    master,
    service,
    selected_services,
    selected_date: str,
    language: str = "ua",
):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS

    duration = service["duration"]

    work_start, work_end = get_work_hours_for_date(
        master["schedule"],
        selected_date,
    )

    if not work_start or not work_end:
        all_times = []
    else:
        all_times = generate_time_slots(
            work_start=work_start,
            work_end=work_end,
            duration=duration,
        )

    busy_bookings = await get_busy_bookings_by_master_and_date(
        master_id=master["id"],
        date=selected_date,
    )

    resource_bookings = await get_bookings_with_resource_by_date(selected_date)

    resource_types = set()

    for item in selected_services:
        selected_service = await get_service_by_id(item["service_id"])
        resource_types.add(selected_service["resource_type"])

    keyboard = []

    for time in all_times:
        slot_start = datetime.strptime(time, "%H:%M")
        slot_end = slot_start + timedelta(minutes=duration)

        slot_is_busy_in_db = False

        for booking in busy_bookings:
            busy_start = datetime.strptime(booking["time"], "%H:%M")
            busy_duration = booking["total_duration"] or service["duration"]
            busy_end = busy_start + timedelta(minutes=busy_duration)

            if times_overlap(slot_start, slot_end, busy_start, busy_end):
                slot_is_busy_in_db = True
                break

        if slot_is_busy_in_db:
            continue

        resource_is_busy = False

        for resource_type in resource_types:
            resource_count = 0

            for booking in resource_bookings:
                if booking["resource_type"] != resource_type:
                    continue

                busy_start = datetime.strptime(booking["time"], "%H:%M")
                busy_duration = booking["total_duration"] or booking["service_duration"]
                busy_end = busy_start + timedelta(minutes=busy_duration)

                if times_overlap(slot_start, slot_end, busy_start, busy_end):
                    resource_count += 1

            if resource_type == "manicure" and resource_count >= 2:
                resource_is_busy = True
                break

            if resource_type == "pedicure" and resource_count >= 1:
                resource_is_busy = True
                break

        if resource_is_busy:
            continue

        if master["calendar_id"]:
            is_free = is_time_free(
                calendar_id=master["calendar_id"],
                date=selected_date,
                time=time,
                duration=duration,
            )

            if not is_free:
                continue

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=time,
                    callback_data=f"select_time:{time}",
                )
            ]
        )

    if not keyboard:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="❌ Немає вільного часу",
                    callback_data="no_free_time",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text=buttons["back"],
                callback_data="back_to_dates",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.callback_query(F.data.startswith("select_date:"))
async def select_date_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    selected_date = callback.data.split(":")[1]

    await state.update_data(date=selected_date)
    await state.set_state(BookingState.choosing_time)

    data = await state.get_data()
    selected_services = data.get("selected_services", [])

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    waiting_text = (
        "⏳ Só um instante...\nEstou verificando os horários disponíveis. ✨"
        if language == "pt"
        else "⏳ Одну хвилинку...\nПеревіряю вільні годинки для запису. ✨"
    )

    await callback.message.answer(waiting_text)

    first_item = selected_services[0]

    master = await get_master_by_id(first_item["master_id"])
    first_service = await get_service_by_id(first_item["service_id"])

    total_duration = 0

    for item in selected_services:
        service = await get_service_by_id(item["service_id"])
        total_duration += service["duration"]

        if item.get("extras"):
            total_duration += sum(
                extra.get("duration", 0) for extra in item.get("extras", [])
            )

    service_for_time = dict(first_service)
    service_for_time["duration"] = total_duration

    await state.update_data(total_duration=total_duration)

    await callback.message.answer(
        texts["choose_time"],
        reply_markup=await times_keyboard(
            master=master,
            service=service_for_time,
            selected_date=selected_date,
            language=language,
        ),
    )

    await callback.answer()


@router.message(F.text.in_(["📅 Записатися", "📅 Marcar"]))
async def start_booking(message: Message, state: FSMContext):
    print("BOOKING BUTTON PRESSED")

    if await stop_blocked_message(message):
        return

    language = await get_user_language(message.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    await state.clear()
    await state.set_state(BookingState.rules)

    await message.answer(
        texts["booking_rules"],
        reply_markup=booking_rules_keyboard(language),
    )


@router.callback_query(F.data == "rules_accept")
async def rules_accept_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    await accept_rules(callback.from_user.id)

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    masters = await get_active_masters()

    if not masters:
        await callback.message.answer(
            "Поки що немає доступних майстрів. Спробуйте пізніше."
        )
        await callback.answer()
        return

    await state.set_state(BookingState.choosing_master)

    await callback.message.answer(
        texts["choose_master"],
        reply_markup=masters_keyboard(masters, language),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("select_master:"))
async def select_master_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    master_id = int(callback.data.split(":")[1])

    await state.update_data(master_id=master_id)
    await state.set_state(BookingState.choosing_category)

    language = await get_user_language(callback.from_user.id)

    categories = await get_service_categories_by_master(master_id)

    if not categories:
        await callback.message.answer("У цього майстра поки що немає доданих послуг.")
        await callback.answer()
        return

    if language == "pt":
        message_text = "💅 Escolha uma categoria:"
    else:
        message_text = "💅 Оберіть категорію послуги:"

    await callback.message.answer(
        message_text,
        reply_markup=service_categories_keyboard(categories, language),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("select_category:"))
async def select_category_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    category_index = int(callback.data.split(":")[1])

    data = await state.get_data()
    master_id = data["master_id"]

    categories = await get_service_categories_by_master(master_id)

    if category_index >= len(categories):
        await callback.answer("Категорію не знайдено", show_alert=True)
        return

    category = categories[category_index]
    category_ua = category["category_ua"]

    await state.update_data(category_ua=category_ua)
    await state.set_state(BookingState.choosing_service)

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    services = await get_services_by_master_and_category(master_id, category_ua)

    if not services:
        await callback.message.answer("У цій категорії поки що немає послуг.")
        await callback.answer()
        return

    await callback.message.answer(
        texts["choose_service"],
        reply_markup=services_keyboard(services, language),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("select_service:"))
async def select_service_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    service_id = int(callback.data.split(":")[1])

    data = await state.get_data()
    selected_services = data.get("selected_services", [])

    service = await get_service_by_id(service_id)

    current_service = {
        "master_id": data["master_id"],
        "service_id": service_id,
        "category_ua": data["category_ua"],
        "price": service["price"],
        "duration": service["duration"],
        "extras": [],
    }

    await state.update_data(
        service_id=service_id,
        selected_extras=[],
        current_service=current_service,
    )

    language = await get_user_language(callback.from_user.id)

    extras = await get_service_extras_by_category(
        master_id=data["master_id"],
        category_ua=data["category_ua"],
    )

    if extras:
        await state.set_state(BookingState.choosing_extras)

        text = (
            "➕ Escolha serviços adicionais:"
            if language == "pt"
            else "➕ Оберіть додаткові послуги:"
        )

        await callback.message.answer(
            text,
            reply_markup=extras_keyboard(extras, [], language),
        )
    else:
        selected_services.append(current_service)

        await state.update_data(
            selected_services=selected_services,
            current_service=None,
        )

        text = (
            "Deseja adicionar outro serviço?"
            if language == "pt"
            else "Бажаєте додати ще одну процедуру?"
        )

        await callback.message.answer(
            text,
            reply_markup=add_another_service_keyboard(language),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("toggle_extra:"))
async def toggle_extra_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    extra_id = int(callback.data.split(":")[1])

    data = await state.get_data()
    current_service = data.get("current_service")
    selected_services = data.get("selected_services", [])

    extra = await get_extra_by_id(extra_id)

    if extra:
        current_service["extras"] = [
            {
                "id": extra["id"],
                "name_ua": extra["name_ua"],
                "name_pt": extra["name_pt"],
                "price": extra["price"],
                "duration": extra["duration"],
            }
        ]
    else:
        current_service["extras"] = []

    selected_services.append(current_service)

    await state.update_data(
        selected_services=selected_services,
        current_service=None,
        selected_extras=[extra_id],
    )

    language = await get_user_language(callback.from_user.id)

    text = (
        "Deseja adicionar outro serviço?"
        if language == "pt"
        else "Бажаєте додати ще одну процедуру?"
    )

    await callback.message.answer(
        text,
        reply_markup=add_another_service_keyboard(language),
    )

    await callback.answer()


@router.callback_query(F.data == "extras_skip")
async def extras_skip_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    data = await state.get_data()
    current_service = data.get("current_service")
    selected_services = data.get("selected_services", [])

    current_service["extras"] = []
    selected_services.append(current_service)

    await state.update_data(
        selected_services=selected_services,
        current_service=None,
        selected_extras=[],
    )

    language = await get_user_language(callback.from_user.id)

    text = (
        "Deseja adicionar outro serviço?"
        if language == "pt"
        else "Бажаєте додати ще одну процедуру?"
    )

    await callback.message.answer(
        text,
        reply_markup=add_another_service_keyboard(language),
    )

    await callback.answer()


@router.callback_query(F.data == "add_another_service")
async def add_another_service_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    masters = await get_active_masters()

    await state.set_state(BookingState.choosing_master)

    await callback.message.answer(
        texts["choose_master"],
        reply_markup=masters_keyboard(masters, language),
    )

    await callback.answer()


@router.callback_query(F.data == "continue_booking")
async def continue_booking_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    await state.set_state(BookingState.choosing_date)

    await callback.message.answer(
        texts["choose_date"],
        reply_markup=dates_keyboard(language),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("select_date:"))
async def select_date_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    selected_date = callback.data.split(":")[1]

    await state.update_data(date=selected_date)
    await state.set_state(BookingState.choosing_time)

    data = await state.get_data()
    selected_services = data.get("selected_services", [])

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    waiting_text = (
        "⏳ Só um instante...\nEstou verificando os horários disponíveis. ✨"
        if language == "pt"
        else "⏳ Одну хвилинку...\nПеревіряю вільні годинки для запису. ✨"
    )

    await callback.message.answer(waiting_text)

    first_item = selected_services[0]
    master = await get_master_by_id(first_item["master_id"])
    first_service = await get_service_by_id(first_item["service_id"])

    total_duration = 0

    for item in selected_services:
        service = await get_service_by_id(item["service_id"])
        total_duration += service["duration"]

        if item.get("extras"):
            total_duration += sum(
                extra.get("duration", 0) for extra in item.get("extras", [])
            )

    service_for_time = dict(first_service)
    service_for_time["duration"] = total_duration

    await state.update_data(total_duration=total_duration)

    await callback.message.answer(
        texts["choose_time"],
        reply_markup=await times_keyboard(
            master=master,
            service=service_for_time,
            selected_services=selected_services,
            selected_date=selected_date,
            language=language,
        ),
    )

    await callback.answer()


@router.callback_query(F.data == "no_free_time")
async def no_free_time_handler(callback: CallbackQuery):
    if await stop_blocked_callback(callback):
        return

    await callback.answer(
        "На цю дату немає вільного часу. Оберіть іншу дату.",
        show_alert=True,
    )


@router.callback_query(F.data.startswith("select_time:"))
async def select_time_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    selected_time = callback.data.split(":", 1)[1]

    await state.update_data(time=selected_time)
    await state.set_state(BookingState.entering_name)

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    await callback.message.answer(texts["enter_name"])

    await callback.answer()


@router.message(BookingState.entering_name)
async def enter_name_handler(message: Message, state: FSMContext):
    if await stop_blocked_message(message):
        return

    await state.update_data(client_name=message.text)
    await state.set_state(BookingState.entering_phone)

    language = await get_user_language(message.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    await message.answer(texts["enter_phone"])


@router.message(BookingState.entering_phone)
async def enter_phone_handler(message: Message, state: FSMContext):
    if await stop_blocked_message(message):
        return

    await state.update_data(client_phone=message.text)
    await state.set_state(BookingState.confirming_booking)

    data = await state.get_data()
    language = await get_user_language(message.from_user.id)

    selected_services = data.get("selected_services", [])

    total_price = 0
    total_duration = 0
    services_lines = []

    for index, item in enumerate(selected_services, start=1):
        master = await get_master_by_id(item["master_id"])
        service = await get_service_by_id(item["service_id"])

        service_name = (
            service["name_pt"]
            if language == "pt" and service["name_pt"]
            else service["name_ua"]
        )

        extras = []
        if item.get("extras"):
            all_extras = await get_service_extras_by_category(
                master_id=item["master_id"],
                category_ua=item["category_ua"],
            )

            extras = [
                extra for extra in all_extras if extra["id"] in item.get("extras", [])
            ]

        extras_price = sum(extra["price"] for extra in extras)
        extras_duration = sum(extra["duration"] for extra in extras)

        service_total_price = service["price"] + extras_price
        service_total_duration = service["duration"] + extras_duration

        total_price += service_total_price
        total_duration += service_total_duration

        if extras:
            extras_text = "\n".join(
                [
                    f"   ➕ {extra['name_pt'] if language == 'pt' and extra['name_pt'] else extra['name_ua']} — {extra['price']}€"
                    for extra in extras
                ]
            )
        else:
            extras_text = (
                "   Sem adicionais" if language == "pt" else "   Без додаткових послуг"
            )

        if language == "pt":
            services_lines.append(
                f"{index}) 👩 Profissional: {master['name']}\n"
                f"   💅 Serviço: {service_name} — {service['price']}€\n"
                f"{extras_text}"
            )
        else:
            services_lines.append(
                f"{index}) 👩 Майстер: {master['name']}\n"
                f"   💅 Послуга: {service_name} — {service['price']}€\n"
                f"{extras_text}"
            )

    await state.update_data(
        total_price=total_price,
        total_duration=total_duration,
    )

    hours = total_duration // 60
    minutes = total_duration % 60

    if language == "pt":
        duration_text = f"{hours} h {minutes} min" if minutes else f"{hours} h"
        services_text = "\n\n".join(services_lines)

        text = (
            "✅ Verifique os dados da marcação:\n\n"
            f"👤 Nome: {data['client_name']}\n"
            f"📞 Telefone: {data['client_phone']}\n\n"
            f"💅 Serviços escolhidos:\n{services_text}\n\n"
            f"📅 Data: {data['date']}\n"
            f"🕒 Hora: {data['time']}\n"
            f"⏳ Duração total: {duration_text}\n"
            f"💶 Total: {total_price}€"
        )
    else:
        duration_text = f"{hours} год {minutes} хв" if minutes else f"{hours} год"
        services_text = "\n\n".join(services_lines)

        text = (
            "✅ Перевірте дані запису:\n\n"
            f"👤 Імʼя: {data['client_name']}\n"
            f"📞 Телефон: {data['client_phone']}\n\n"
            f"💅 Обрані процедури:\n{services_text}\n\n"
            f"📅 Дата: {data['date']}\n"
            f"🕒 Час: {data['time']}\n"
            f"⏳ Загальна тривалість: {duration_text}\n"
            f"💶 До оплати: {total_price}€"
        )

    await message.answer(text, reply_markup=booking_confirm_keyboard(language))


@router.callback_query(F.data == "confirm_booking")
async def confirm_booking_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    data = await state.get_data()

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    user = await get_user_by_telegram_id(callback.from_user.id)

    selected_services = data.get("selected_services", [])

    if not selected_services:
        await callback.answer("Помилка: послуги не вибрані", show_alert=True)
        return

    total_price = 0
    total_duration = 0

    for item in selected_services:
        total_price += item.get("price", 0)
        total_duration += item.get("duration", 0)

        for extra in item.get("extras", []):
            total_price += extra.get("price", 0)
            total_duration += extra.get("duration", 0)

    main_service = selected_services[0]

    booking_id = await create_booking(
        client_id=user["id"],
        master_id=main_service["master_id"],
        service_id=main_service["service_id"],
        client_name=data["client_name"],
        client_phone=data["client_phone"],
        date=data["date"],
        time=data["time"],
        total_price=total_price,
        total_duration=total_duration,
        selected_extras=[],
    )

    for index, item in enumerate(selected_services, start=1):
        service_price = item.get("price", 0)
        service_duration = item.get("duration", 0)

        for extra in item.get("extras", []):
            service_price += extra.get("price", 0)
            service_duration += extra.get("duration", 0)

        await add_booking_service(
            booking_id=booking_id,
            master_id=item["master_id"],
            service_id=item["service_id"],
            extras=item.get("extras", []),
            position=index,
            price=service_price,
            duration=service_duration,
        )

    await update_booking_status(booking_id, "waiting_confirmation")
    await update_payment_status(booking_id, "not_required")

    await notify_master_about_booking(
        bot=callback.bot,
        booking_id=booking_id,
    )

    await state.update_data(booking_id=booking_id)

    await state.set_state(BookingState.waiting_master_confirmation)

    await callback.message.answer(
        texts["waiting_confirmation"],
        reply_markup=main_menu(language),
    )

    await callback.answer()


@router.callback_query(F.data == "deposit_paid")
async def deposit_paid_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    data = await state.get_data()
    booking_id = data.get("booking_id")

    if booking_id:
        await update_booking_status(booking_id, "waiting_confirmation")
        await update_payment_status(booking_id, "waiting_confirmation")

        await notify_master_about_booking(
            bot=callback.bot,
            booking_id=booking_id,
        )

    await state.set_state(BookingState.waiting_master_confirmation)

    await callback.message.answer(
        texts["waiting_confirmation"],
        reply_markup=main_menu(language),
    )

    await callback.answer()


@router.callback_query(F.data == "change_booking")
async def change_booking_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    masters = await get_active_masters()

    await state.set_state(BookingState.choosing_master)

    await callback.message.answer(
        texts["choose_master"],
        reply_markup=masters_keyboard(masters, language),
    )

    await callback.answer()


@router.callback_query(F.data == "back_to_masters")
async def back_to_masters_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    masters = await get_active_masters()

    await state.set_state(BookingState.choosing_master)

    await callback.message.answer(
        texts["choose_master"],
        reply_markup=masters_keyboard(masters, language),
    )

    await callback.answer()


@router.callback_query(F.data == "back_to_services")
async def back_to_services_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    data = await state.get_data()

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    services = await get_services_by_master_and_category(
        data["master_id"],
        data["category_ua"],
    )

    await state.set_state(BookingState.choosing_service)

    await callback.message.answer(
        texts["choose_service"],
        reply_markup=services_keyboard(services, language),
    )

    await callback.answer()


@router.callback_query(F.data == "back_to_dates")
async def back_to_dates_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    await state.set_state(BookingState.choosing_date)

    await callback.message.answer(
        texts["choose_date"],
        reply_markup=dates_keyboard(language),
    )

    await callback.answer()


@router.callback_query(F.data == "back_main")
async def back_main_handler(callback: CallbackQuery, state: FSMContext):
    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    await state.clear()

    await callback.message.answer(texts["main_menu"], reply_markup=main_menu(language))

    await callback.answer()


@router.callback_query(F.data == "back_to_categories")
async def back_to_categories_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    data = await state.get_data()

    language = await get_user_language(callback.from_user.id)

    categories = await get_service_categories_by_master(data["master_id"])

    await state.set_state(BookingState.choosing_category)

    if language == "pt":
        message_text = "💅 Escolha uma categoria:"
    else:
        message_text = "💅 Оберіть категорію послуги:"

    await callback.message.answer(
        message_text,
        reply_markup=service_categories_keyboard(categories, language),
    )

    await callback.answer()
