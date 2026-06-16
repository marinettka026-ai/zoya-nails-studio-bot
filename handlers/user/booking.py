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
    update_booking_status,
    update_payment_status,
    get_service_categories_by_master,
    get_services_by_master_and_category,
    get_busy_bookings_by_master_and_date,
)

from services.notifications import notify_master_about_booking

from keyboards.inline import (
    booking_rules_keyboard,
    booking_confirm_keyboard,
    deposit_keyboard,
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

    for category in categories:
        category_name = (
            category["category_pt"]
            if language == "pt" and category["category_pt"]
            else category["category_ua"]
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"💅 {category_name}",
                    callback_data=f"select_category:{category['category_ua']}",
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


def dates_keyboard(language: str = "ua"):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS
    keyboard = []

    today = datetime.now()

    for i in range(7):
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


def generate_time_slots(
    work_start: str = "09:30",
    work_end: str = "17:30",
    duration: int = 60,
    step: int = 30,
):
    slots = []

    start = datetime.strptime(work_start, "%H:%M")
    end = datetime.strptime(work_end, "%H:%M")

    current = start

    while current + timedelta(minutes=duration) <= end:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=step)

    return slots


def times_overlap(start_1, end_1, start_2, end_2):
    return start_1 < end_2 and start_2 < end_1


async def times_keyboard(
    master,
    service,
    selected_date: str,
    language: str = "ua",
):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS

    duration = service["duration"]
    all_times = generate_time_slots(duration=duration)

    busy_bookings = await get_busy_bookings_by_master_and_date(
        master_id=master["id"],
        date=selected_date,
    )

    keyboard = []

    for time in all_times:
        slot_start = datetime.strptime(time, "%H:%M")
        slot_end = slot_start + timedelta(minutes=duration)

        slot_is_busy_in_db = False

        for booking in busy_bookings:
            busy_start = datetime.strptime(booking["time"], "%H:%M")
            busy_end = busy_start + timedelta(minutes=booking["duration"])

            if times_overlap(slot_start, slot_end, busy_start, busy_end):
                slot_is_busy_in_db = True
                print(
                    f"DB BUSY {selected_date} {time} "
                    f"| busy={booking['time']} duration={booking['duration']}"
                )
                break

        if slot_is_busy_in_db:
            continue

        if master["calendar_id"]:
            is_free = is_time_free(
                calendar_id=master["calendar_id"],
                date=selected_date,
                time=time,
                duration=duration,
            )

            print(
                f"GOOGLE CHECK {selected_date} {time} "
                f"| duration={duration} | free={is_free}"
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

    category_ua = callback.data.split(":", 1)[1]

    await state.update_data(category_ua=category_ua)
    await state.set_state(BookingState.choosing_service)

    data = await state.get_data()
    master_id = data["master_id"]

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

    await state.update_data(service_id=service_id)
    await state.set_state(BookingState.choosing_date)

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

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

    master = await get_master_by_id(data["master_id"])
    service = await get_service_by_id(data["service_id"])

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    await callback.message.answer(
        texts["choose_time"],
        reply_markup=await times_keyboard(
            master=master,
            service=service,
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
    texts, _ = get_texts_and_buttons(language)

    master = await get_master_by_id(data["master_id"])
    service = await get_service_by_id(data["service_id"])

    service_name = (
        service["name_pt"]
        if language == "pt" and service["name_pt"]
        else service["name_ua"]
    )

    text = texts["booking_details"].format(
        client_name=data["client_name"],
        client_phone=data["client_phone"],
        master_name=master["name"],
        service_name=service_name,
        date=data["date"],
        time=data["time"],
        deposit=service["deposit_amount"],
    )

    await message.answer(text, reply_markup=booking_confirm_keyboard(language))


@router.callback_query(F.data == "confirm_booking")
async def confirm_booking_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    data = await state.get_data()

    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    service = await get_service_by_id(data["service_id"])

    user = await get_user_by_telegram_id(callback.from_user.id)

    booking_id = await create_booking(
        client_id=user["id"],
        master_id=data["master_id"],
        service_id=data["service_id"],
        client_name=data["client_name"],
        client_phone=data["client_phone"],
        date=data["date"],
        time=data["time"],
    )

    await state.update_data(booking_id=booking_id)
    await state.set_state(BookingState.waiting_deposit)

    text = texts["deposit"].format(payment_details=PAYMENT_DETAILS)

    await callback.message.answer(text, reply_markup=deposit_keyboard(language))

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
