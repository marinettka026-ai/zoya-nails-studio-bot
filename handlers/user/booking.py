import asyncio
import calendar
from datetime import date, datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from database.queries import (
    accept_rules,
    create_booking_from_selected_services,
    get_active_masters,
    get_extra_by_id,
    get_master_by_id,
    get_service_by_id,
    get_service_categories_by_master,
    get_service_extras_by_category,
    get_services_by_master,
    get_user_by_telegram_id,
    is_selected_services_available,
    update_user_phone,
)
from keyboards.inline import booking_confirm_keyboard, booking_rules_keyboard
from keyboards.menus import main_menu
from keyboards.reply import phone_keyboard, remove_reply_keyboard
from locales.pt import BUTTONS as PT_BUTTONS
from locales.pt import TEXTS as PT_TEXTS
from locales.ua import BUTTONS as UA_BUTTONS
from locales.ua import TEXTS as UA_TEXTS
from services.calendar import get_busy_intervals, slot_overlaps_busy
from services.notifications import notify_master_about_booking
from states.booking_state import BookingState

router = Router()

DAY_NAMES_UA = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Нд",
}

MONTHS_UA = {
    1: "Січень",
    2: "Лютий",
    3: "Березень",
    4: "Квітень",
    5: "Травень",
    6: "Червень",
    7: "Липень",
    8: "Серпень",
    9: "Вересень",
    10: "Жовтень",
    11: "Листопад",
    12: "Грудень",
}

MONTHS_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


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


async def stop_blocked_callback(callback: CallbackQuery) -> bool:
    if not await is_user_blocked(callback.from_user.id):
        return False

    language = await get_user_language(callback.from_user.id)
    text = (
        "⛔ A marcação através do bot não está disponível para si.\n\n"
        "Por favor, contacte a profissional diretamente."
        if language == "pt"
        else "⛔ Запис через бота для вас недоступний.\n\n"
        "Будь ласка, зв’яжіться з майстром напряму."
    )
    await callback.message.answer(text)
    await callback.answer()
    return True


async def stop_blocked_message(message: Message) -> bool:
    if not await is_user_blocked(message.from_user.id):
        return False

    language = await get_user_language(message.from_user.id)
    text = (
        "⛔ A marcação através do bot não está disponível para si.\n\n"
        "Por favor, contacte a profissional diretamente."
        if language == "pt"
        else "⛔ Запис через бота для вас недоступний.\n\n"
        "Будь ласка, зв’яжіться з майстром напряму."
    )
    await message.answer(text)
    return True


def masters_keyboard(masters, language: str = "ua"):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"🌸 {master['name']}",
                callback_data=f"select_master:{master['id']}",
            )
        ]
        for master in masters
    ]
    keyboard.append(
        [InlineKeyboardButton(text=buttons["back"], callback_data="back_main")]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Залишено тимчасово для сумісності з profile.py.
def service_categories_keyboard(categories, language: str = "ua"):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS
    keyboard = []

    for index, category in enumerate(categories):
        name = (
            category["category_pt"]
            if language == "pt" and category["category_pt"]
            else category["category_ua"]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"💅 {name}",
                    callback_data=f"legacy_category:{index}",
                )
            ]
        )

    keyboard.append(
        [InlineKeyboardButton(text=buttons["back"], callback_data="back_to_masters")]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def gender_keyboard(language: str = "ua"):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS

    if language == "pt":
        female = "👩 Serviços femininos"
        male = "👨 Serviços masculinos"
    else:
        female = "👩 Жіночі послуги"
        male = "👨 Чоловічі послуги"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=female, callback_data="select_gender:female")],
            [InlineKeyboardButton(text=male, callback_data="select_gender:male")],
            [
                InlineKeyboardButton(
                    text=buttons["back"], callback_data="back_to_masters"
                )
            ],
        ]
    )


def is_male_text(*values) -> bool:
    text = " ".join(str(value or "").lower() for value in values)
    markers = ("чолов", "муж", "mascul", "homem")
    return any(marker in text for marker in markers)


def service_matches_gender(service, gender: str) -> bool:
    male = is_male_text(
        service["category_ua"],
        service["category_pt"],
        service["name_ua"],
        service["name_pt"],
    )
    return male if gender == "male" else not male


async def get_catalog(master_id: int, gender: str):
    services = await get_services_by_master(master_id)
    services = [
        service for service in services if service_matches_gender(service, gender)
    ]

    extras = []
    seen_extra_ids = set()

    categories = await get_service_categories_by_master(master_id)
    for category in categories:
        category_ua = category["category_ua"]
        if not category_ua:
            continue

        category_is_male = is_male_text(category_ua, category["category_pt"])
        if (gender == "male") != category_is_male:
            continue

        category_extras = await get_service_extras_by_category(
            master_id=master_id,
            category_ua=category_ua,
        )
        for extra in category_extras:
            if extra["id"] not in seen_extra_ids:
                extras.append(extra)
                seen_extra_ids.add(extra["id"])

    return services, extras


def services_checklist_keyboard(
    services,
    extras,
    selected_service_ids,
    selected_extra_ids,
    language: str = "ua",
):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS
    keyboard = []

    for service in services:
        service_id = service["id"]
        mark = "✅" if service_id in selected_service_ids else "⬜"
        name = (
            service["name_pt"]
            if language == "pt" and service["name_pt"]
            else service["name_ua"]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {name} — {service['price']}€",
                    callback_data=f"toggle_service:{service_id}",
                )
            ]
        )

    if extras:
        divider = "➕ Adicionais" if language == "pt" else "➕ Додаткові послуги"
        keyboard.append([InlineKeyboardButton(text=divider, callback_data="noop")])

        for extra in extras:
            extra_id = extra["id"]
            mark = "✅" if extra_id in selected_extra_ids else "⬜"
            name = (
                extra["name_pt"]
                if language == "pt" and extra["name_pt"]
                else extra["name_ua"]
            )
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=f"{mark} {name} — {extra['price']}€",
                        callback_data=f"toggle_catalog_extra:{extra_id}",
                    )
                ]
            )

    continue_text = "➡️ Continuar" if language == "pt" else "➡️ Продовжити"
    keyboard.append(
        [InlineKeyboardButton(text=continue_text, callback_data="services_continue")]
    )
    keyboard.append(
        [InlineKeyboardButton(text=buttons["back"], callback_data="back_to_gender")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def build_selected_services_from_state(data: dict):
    master_id = data["master_id"]
    selected_service_ids = list(dict.fromkeys(data.get("selected_service_ids", [])))
    selected_extra_ids = list(dict.fromkeys(data.get("selected_extra_ids", [])))

    result = []
    category_to_item = {}

    for service_id in selected_service_ids:
        service = await get_service_by_id(service_id)
        if not service or service["master_id"] != master_id:
            continue

        item = {
            "master_id": master_id,
            "service_id": service_id,
            "category_ua": service["category_ua"],
            "price": service["price"],
            "duration": service["duration"],
            "extras": [],
        }
        result.append(item)
        category_to_item.setdefault(service["category_ua"], item)

    orphan_extras = []

    for extra_id in selected_extra_ids:
        extra = await get_extra_by_id(extra_id)
        if not extra or extra["master_id"] != master_id:
            continue

        parent = category_to_item.get(extra["category_ua"])
        if not parent:
            orphan_extras.append(extra)
            continue

        parent["extras"].append(
            {
                "id": extra["id"],
                "name_ua": extra["name_ua"],
                "name_pt": extra["name_pt"],
                "price": extra["price"],
                "duration": extra["duration"],
            }
        )

    return result, orphan_extras


def get_work_hours_for_date(schedule: str, selected_date: str):
    if not schedule:
        return None, None

    selected_weekday = datetime.strptime(selected_date, "%Y-%m-%d").weekday()
    day_name = DAY_NAMES_UA[selected_weekday]

    for line in schedule.splitlines():
        line = line.strip()
        if not line or not line.startswith(day_name):
            continue

        lowered = line.lower()
        if "вихідний" in lowered or "folga" in lowered:
            return None, None

        if ":" not in line:
            continue

        _, hours = line.split(":", 1)
        if "-" not in hours:
            continue

        work_start, work_end = hours.strip().split("-", 1)
        return work_start.strip(), work_end.strip()

    return None, None


def generate_time_slots(work_start: str, work_end: str, step: int = 30):
    slots = []
    current = datetime.strptime(work_start, "%H:%M")
    end = datetime.strptime(work_end, "%H:%M")

    while current <= end:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=step)

    return slots


async def get_total_duration(selected_services: list[dict]) -> int:
    total = 0
    for item in selected_services:
        service = await get_service_by_id(item["service_id"])
        if not service:
            continue
        total += int(service["duration"])
        total += sum(int(extra.get("duration", 0)) for extra in item.get("extras", []))
    return total


async def get_available_times(master, selected_services, selected_date: str):
    work_start, work_end = get_work_hours_for_date(
        master["schedule"],
        selected_date,
    )
    if not work_start or not work_end:
        return []

    total_duration = await get_total_duration(selected_services)
    if total_duration <= 0:
        return []

    available_times = []
    work_end_dt = datetime.strptime(work_end, "%H:%M")
    today = date.today()
    selected_day = datetime.strptime(
        selected_date,
        "%Y-%m-%d",
    ).date()

    busy_intervals = []

    if master["calendar_id"]:
        try:
            busy_intervals = await asyncio.to_thread(
                get_busy_intervals,
                calendar_id=master["calendar_id"],
                date=selected_date,
                start_time=work_start,
                end_time=work_end,
            )
        except Exception as error:
            print("GOOGLE CALENDAR CHECK ERROR:", repr(error))
            return []

    for time_str in generate_time_slots(work_start, work_end):
        slot_start = datetime.strptime(time_str, "%H:%M")
        slot_end = slot_start + timedelta(minutes=total_duration)

        if slot_end > work_end_dt:
            continue

        if selected_day == today:
            now = datetime.now()
            candidate = datetime.combine(
                today,
                slot_start.time(),
            )
            if candidate <= now:
                continue

        available = await is_selected_services_available(
            selected_services=selected_services,
            date=selected_date,
            start_time=time_str,
        )
        if not available:
            continue

        if busy_intervals and slot_overlaps_busy(
            date=selected_date,
            time=time_str,
            duration=total_duration,
            busy_intervals=busy_intervals,
        ):
            continue

        available_times.append(time_str)

    return available_times


def date_can_be_selected(master, selected_date: str) -> bool:
    work_start, work_end = get_work_hours_for_date(
        master["schedule"],
        selected_date,
    )
    return bool(work_start and work_end)


async def date_has_available_time(
    master,
    selected_services,
    selected_date: str,
) -> bool:
    if not date_can_be_selected(master, selected_date):
        return False

    times = await get_available_times(
        master,
        selected_services,
        selected_date,
    )
    return bool(times)


async def calendar_keyboard(
    master,
    selected_services,
    year: int,
    month: int,
    language: str = "ua",
):
    today = date.today()
    max_date = today + timedelta(days=60)
    month_names = MONTHS_PT if language == "pt" else MONTHS_UA
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS

    keyboard = [
        [
            InlineKeyboardButton(
                text=f"📅 {month_names[month]} {year}", callback_data="noop"
            )
        ]
    ]

    weekdays = (
        ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        if language == "pt"
        else ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
    )
    keyboard.append(
        [InlineKeyboardButton(text=day, callback_data="noop") for day in weekdays]
    )

    cal = calendar.Calendar(firstweekday=0)
    month_weeks = cal.monthdatescalendar(year, month)

    dates_to_check = []
    for week in month_weeks:
        for day in week:
            if (
                day.month == month
                and today <= day <= max_date
                and date_can_be_selected(master, day.strftime("%Y-%m-%d"))
            ):
                dates_to_check.append(day)

    availability = {}
    if dates_to_check:
        results = await asyncio.gather(
            *[
                date_has_available_time(
                    master,
                    selected_services,
                    day.strftime("%Y-%m-%d"),
                )
                for day in dates_to_check
            ],
            return_exceptions=True,
        )

        for day, result in zip(dates_to_check, results):
            availability[day] = (
                bool(result) if not isinstance(result, Exception) else False
            )

    for week in month_weeks:
        row = []

        for day in week:
            if day.month != month or day < today or day > max_date:
                row.append(
                    InlineKeyboardButton(
                        text="·",
                        callback_data="noop",
                    )
                )
                continue

            selected_date = day.strftime("%Y-%m-%d")

            if availability.get(day, False):
                row.append(
                    InlineKeyboardButton(
                        text=f"🟢 {day.day}",
                        callback_data=f"select_date:{selected_date}",
                    )
                )
            else:
                row.append(
                    InlineKeyboardButton(
                        text=f"❌ {day.day}",
                        callback_data="noop",
                    )
                )

        keyboard.append(row)

    current_first = date(today.year, today.month, 1)
    shown_first = date(year, month, 1)

    prev_month = shown_first.replace(day=1) - timedelta(days=1)
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    nav = []
    if shown_first > current_first:
        nav.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=f"calendar_month:{prev_month.year}:{prev_month.month}",
            )
        )
    nav.append(InlineKeyboardButton(text=" ", callback_data="noop"))
    if date(next_year, next_month, 1) <= max_date:
        nav.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"calendar_month:{next_year}:{next_month}",
            )
        )
    keyboard.append(nav)

    nearest = (
        "⚡ Próximo horário disponível"
        if language == "pt"
        else "⚡ Найближчий вільний час"
    )
    keyboard.append(
        [InlineKeyboardButton(text=nearest, callback_data="nearest_free_time")]
    )
    keyboard.append(
        [InlineKeyboardButton(text=buttons["back"], callback_data="back_to_services")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def times_keyboard(times: list[str], language: str = "ua"):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS
    keyboard = []

    for index in range(0, len(times), 3):
        keyboard.append(
            [
                InlineKeyboardButton(text=time, callback_data=f"select_time:{time}")
                for time in times[index : index + 3]
            ]
        )

    if not times:
        text = (
            "❌ Sem horários livres" if language == "pt" else "❌ Немає вільного часу"
        )
        keyboard.append([InlineKeyboardButton(text=text, callback_data="noop")])

    keyboard.append(
        [InlineKeyboardButton(text=buttons["back"], callback_data="back_to_dates")]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def send_masters(message: Message, state: FSMContext, language: str):
    texts, _ = get_texts_and_buttons(language)
    masters = await get_active_masters()

    if not masters:
        text = (
            "De momento não existem profissionais disponíveis."
            if language == "pt"
            else "Поки що немає доступних майстрів. Спробуйте пізніше."
        )
        await message.answer(text)
        return

    await state.set_state(BookingState.choosing_master)
    await message.answer(
        texts["choose_master"], reply_markup=masters_keyboard(masters, language)
    )


async def send_gender_choice(message: Message, state: FSMContext, language: str):
    text = (
        "💅 Escolha o tipo de serviços:"
        if language == "pt"
        else "💅 Оберіть тип послуг:"
    )
    await state.set_state(BookingState.choosing_gender)
    await message.answer(text, reply_markup=gender_keyboard(language))


async def send_service_checklist(message: Message, state: FSMContext, language: str):
    data = await state.get_data()
    master_id = data["master_id"]
    gender = data["gender"]
    services, extras = await get_catalog(master_id, gender)

    if not services:
        text = (
            "Não há serviços nesta categoria."
            if language == "pt"
            else "У цій категорії поки немає послуг."
        )
        await message.answer(text)
        return

    selected_service_ids = data.get("selected_service_ids", [])
    selected_extra_ids = data.get("selected_extra_ids", [])

    text = (
        "💅 Selecione tudo o que precisa. Pode escolher vários serviços:"
        if language == "pt"
        else "💅 Позначте все, що вам потрібно. Можна обрати декілька послуг:"
    )
    await state.set_state(BookingState.choosing_services)
    await message.answer(
        text,
        reply_markup=services_checklist_keyboard(
            services,
            extras,
            selected_service_ids,
            selected_extra_ids,
            language,
        ),
    )


async def send_calendar(
    message: Message, state: FSMContext, language: str, year=None, month=None
):
    data = await state.get_data()
    selected_services = data.get("selected_services", [])
    if not selected_services:
        text = (
            "Selecione pelo menos um serviço."
            if language == "pt"
            else "Оберіть хоча б одну послугу."
        )
        await message.answer(text)
        return

    master = await get_master_by_id(data["master_id"])
    today = date.today()
    year = year or today.year
    month = month or today.month

    text = (
        "📅 Escolha uma data.\n\n🟢 — há horários livres\n❌ — não há horários livres"
        if language == "pt"
        else "📅 Оберіть дату.\n\n🟢 — є вільні години\n❌ — вільних годин немає"
    )
    await state.set_state(BookingState.choosing_date)
    await message.answer(
        text,
        reply_markup=await calendar_keyboard(
            master, selected_services, year, month, language
        ),
    )


async def send_confirmation(message: Message, state: FSMContext, language: str):
    data = await state.get_data()
    selected_services = data.get("selected_services", [])
    master = await get_master_by_id(data["master_id"])

    total_price = 0.0
    total_duration = 0
    lines = []

    for item in selected_services:
        service = await get_service_by_id(item["service_id"])
        if not service:
            continue

        name = (
            service["name_pt"]
            if language == "pt" and service["name_pt"]
            else service["name_ua"]
        )
        item_price = float(service["price"])
        item_duration = int(service["duration"])
        lines.append(f"• {name} — {service['price']}€")

        for extra in item.get("extras", []):
            extra_name = (
                extra["name_pt"]
                if language == "pt" and extra.get("name_pt")
                else extra["name_ua"]
            )
            lines.append(f"  + {extra_name} — {extra['price']}€")
            item_price += float(extra.get("price", 0))
            item_duration += int(extra.get("duration", 0))

        total_price += item_price
        total_duration += item_duration

    hours, minutes = divmod(total_duration, 60)
    if language == "pt":
        duration_text = f"{hours} h {minutes} min" if minutes else f"{hours} h"
        text = (
            "✅ Confirme a sua marcação:\n\n"
            f"👩 Profissional: {master['name']}\n"
            f"💅 Serviços:\n" + "\n".join(lines) + "\n\n"
            f"📅 Data: {data['date']}\n"
            f"🕒 Hora: {data['time']}\n"
            f"⏳ Duração: {duration_text}\n"
            f"💶 Total: {total_price:g}€\n"
            f"📱 Telefone: {data['client_phone']}"
        )
    else:
        duration_text = f"{hours} год {minutes} хв" if minutes else f"{hours} год"
        text = (
            "✅ Підтвердіть запис:\n\n"
            f"👩 Майстер: {master['name']}\n"
            f"💅 Послуги:\n" + "\n".join(lines) + "\n\n"
            f"📅 Дата: {data['date']}\n"
            f"🕒 Час: {data['time']}\n"
            f"⏳ Тривалість: {duration_text}\n"
            f"💶 Вартість: {total_price:g}€\n"
            f"📱 Телефон: {data['client_phone']}"
        )

    await state.update_data(total_price=total_price, total_duration=total_duration)
    await state.set_state(BookingState.confirming_booking)
    await message.answer(text, reply_markup=booking_confirm_keyboard(language))


@router.message(F.text.in_(["📅 Записатися", "📅 Marcar"]))
async def start_booking(message: Message, state: FSMContext):
    if await stop_blocked_message(message):
        return

    language = await get_user_language(message.from_user.id)
    user = await get_user_by_telegram_id(message.from_user.id)
    await state.clear()

    if user and user["rules_accepted"]:
        await send_masters(message, state, language)
        return

    texts, _ = get_texts_and_buttons(language)
    await state.set_state(BookingState.rules)
    await message.answer(
        texts["booking_rules"], reply_markup=booking_rules_keyboard(language)
    )


@router.callback_query(F.data == "rules_accept")
async def rules_accept_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    await accept_rules(callback.from_user.id)
    language = await get_user_language(callback.from_user.id)
    await send_masters(callback.message, state, language)
    await callback.answer()


@router.callback_query(F.data.startswith("select_master:"))
async def select_master_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    master_id = int(callback.data.split(":", 1)[1])
    await state.update_data(
        master_id=master_id,
        selected_service_ids=[],
        selected_extra_ids=[],
        selected_services=[],
    )

    language = await get_user_language(callback.from_user.id)
    await send_gender_choice(callback.message, state, language)
    await callback.answer()


@router.callback_query(F.data.startswith("select_gender:"))
async def select_gender_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    gender = callback.data.split(":", 1)[1]
    await state.update_data(gender=gender)
    language = await get_user_language(callback.from_user.id)
    await send_service_checklist(callback.message, state, language)
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_service:"))
async def toggle_service_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    service_id = int(callback.data.split(":", 1)[1])
    data = await state.get_data()
    selected = data.get("selected_service_ids", [])

    if service_id in selected:
        selected.remove(service_id)
    else:
        selected.append(service_id)

    await state.update_data(selected_service_ids=selected)
    language = await get_user_language(callback.from_user.id)

    services, extras = await get_catalog(data["master_id"], data["gender"])
    await callback.message.edit_reply_markup(
        reply_markup=services_checklist_keyboard(
            services,
            extras,
            selected,
            data.get("selected_extra_ids", []),
            language,
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_catalog_extra:"))
async def toggle_catalog_extra_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    extra_id = int(callback.data.split(":", 1)[1])
    data = await state.get_data()
    selected = data.get("selected_extra_ids", [])

    if extra_id in selected:
        selected.remove(extra_id)
    else:
        selected.append(extra_id)

    await state.update_data(selected_extra_ids=selected)
    language = await get_user_language(callback.from_user.id)

    services, extras = await get_catalog(data["master_id"], data["gender"])
    await callback.message.edit_reply_markup(
        reply_markup=services_checklist_keyboard(
            services,
            extras,
            data.get("selected_service_ids", []),
            selected,
            language,
        )
    )
    await callback.answer()


@router.callback_query(F.data == "services_continue")
async def services_continue_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    data = await state.get_data()
    language = await get_user_language(callback.from_user.id)
    selected_services, orphan_extras = await build_selected_services_from_state(data)

    if not selected_services:
        text = (
            "Selecione pelo menos um serviço."
            if language == "pt"
            else "Оберіть хоча б одну основну послугу."
        )
        await callback.answer(text, show_alert=True)
        return

    if orphan_extras:
        text = (
            "Para um adicional, selecione também o serviço principal correspondente."
            if language == "pt"
            else "Для додаткової послуги оберіть також відповідну основну процедуру."
        )
        await callback.answer(text, show_alert=True)
        return

    await state.update_data(selected_services=selected_services)

    loading_text = (
        "⏳ A verificar os dias disponíveis..."
        if language == "pt"
        else "⏳ Зачекайте, перевіряю вільні дати..."
    )
    await callback.message.answer(loading_text)
    await callback.answer()

    await send_calendar(
        callback.message,
        state,
        language,
    )


@router.callback_query(F.data.startswith("calendar_month:"))
async def calendar_month_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    _, year, month = callback.data.split(":")
    language = await get_user_language(callback.from_user.id)
    data = await state.get_data()
    master = await get_master_by_id(data["master_id"])

    await callback.message.edit_reply_markup(
        reply_markup=await calendar_keyboard(
            master,
            data["selected_services"],
            int(year),
            int(month),
            language,
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("select_date:"))
async def select_date_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    selected_date = callback.data.split(":", 1)[1]
    language = await get_user_language(callback.from_user.id)

    loading_text = (
        "⏳ Aguarde um momento, estou a procurar horários livres..."
        if language == "pt"
        else "⏳ Зачекайте трішки, шукаю вільні годинки..."
    )
    loading_message = await callback.message.answer(loading_text)
    await callback.answer()

    data = await state.get_data()
    master = await get_master_by_id(data["master_id"])

    times = await get_available_times(
        master,
        data["selected_services"],
        selected_date,
    )

    if not times:
        text = (
            "❌ Já não existem horários livres neste dia. Escolha outra data."
            if language == "pt"
            else "❌ На цей день вільних годин уже немає. Оберіть іншу дату."
        )
        await loading_message.edit_text(text)
        return

    await state.update_data(date=selected_date)
    await state.set_state(BookingState.choosing_time)

    text = "🕒 Escolha a hora:" if language == "pt" else "🕒 Оберіть вільний час:"
    await loading_message.edit_text(
        text,
        reply_markup=times_keyboard(times, language),
    )


@router.callback_query(F.data == "nearest_free_time")
async def nearest_free_time_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    language = await get_user_language(callback.from_user.id)

    loading_text = (
        "⏳ Aguarde um momento, estou a procurar o horário livre mais próximo..."
        if language == "pt"
        else "⏳ Зачекайте трішки, шукаю найближчі вільні годинки..."
    )
    loading_message = await callback.message.answer(loading_text)
    await callback.answer()

    data = await state.get_data()
    master = await get_master_by_id(data["master_id"])
    selected_services = data["selected_services"]

    for offset in range(61):
        candidate_date = date.today() + timedelta(days=offset)
        date_str = candidate_date.strftime("%Y-%m-%d")

        times = await get_available_times(
            master,
            selected_services,
            date_str,
        )

        if times:
            await state.update_data(date=date_str)
            await state.set_state(BookingState.choosing_time)

            text = (
                f"⚡ Próxima data disponível: {candidate_date.strftime('%d.%m.%Y')}"
                if language == "pt"
                else f"⚡ Найближча вільна дата: {candidate_date.strftime('%d.%m.%Y')}"
            )
            await loading_message.edit_text(
                text,
                reply_markup=times_keyboard(times, language),
            )
            return

    text = (
        "❌ Não encontrei horários livres nos próximos 60 dias."
        if language == "pt"
        else "❌ Не знайшла вільного часу на найближчі 60 днів."
    )
    await loading_message.edit_text(text)


@router.callback_query(F.data.startswith("select_time:"))
async def select_time_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    selected_time = callback.data.split(":", 1)[1]
    await state.update_data(time=selected_time)

    user = await get_user_by_telegram_id(callback.from_user.id)
    language = await get_user_language(callback.from_user.id)

    client_name = (
        user["name"] if user and user["name"] else None
    ) or callback.from_user.full_name
    await state.update_data(client_name=client_name)

    if user and user["phone"]:
        await state.update_data(client_phone=user["phone"])
        await send_confirmation(callback.message, state, language)
    else:
        await state.set_state(BookingState.sharing_phone)
        text = (
            "📱 Partilhe o seu número de telefone para confirmar a marcação."
            if language == "pt"
            else "📱 Поділіться номером телефону для підтвердження запису."
        )
        await callback.message.answer(text, reply_markup=phone_keyboard(language))

    await callback.answer()


@router.message(BookingState.sharing_phone, F.contact)
async def receive_phone_handler(message: Message, state: FSMContext):
    if await stop_blocked_message(message):
        return

    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        language = await get_user_language(message.from_user.id)
        text = (
            "Partilhe o seu próprio número."
            if language == "pt"
            else "Будь ласка, поділіться саме своїм номером."
        )
        await message.answer(text)
        return

    phone = message.contact.phone_number
    await update_user_phone(message.from_user.id, phone)
    await state.update_data(client_phone=phone)

    language = await get_user_language(message.from_user.id)
    await message.answer("✅", reply_markup=remove_reply_keyboard())
    await send_confirmation(message, state, language)


@router.message(BookingState.sharing_phone)
async def phone_only_by_button_handler(message: Message):
    language = await get_user_language(message.from_user.id)
    text = (
        "Use o botão abaixo para partilhar o número de telefone."
        if language == "pt"
        else "Натисніть кнопку нижче, щоб поділитися номером телефону."
    )
    await message.answer(text, reply_markup=phone_keyboard(language))


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
        await callback.answer("Послуги не вибрані", show_alert=True)
        return

    booking_id = await create_booking_from_selected_services(
        client_id=user["id"],
        selected_services=selected_services,
        client_name=data["client_name"],
        client_phone=data["client_phone"],
        date=data["date"],
        start_time=data["time"],
        comment=data.get("comment"),
    )

    if not booking_id:
        text = (
            "Este horário já não está disponível."
            if language == "pt"
            else "На жаль, цей час уже зайнятий. Оберіть інший."
        )
        await callback.answer(text, show_alert=True)
        return

    await notify_master_about_booking(bot=callback.bot, booking_id=booking_id)
    await state.update_data(booking_id=booking_id)
    await state.set_state(BookingState.waiting_master_confirmation)
    await callback.message.answer(
        texts["waiting_confirmation"], reply_markup=main_menu(language)
    )
    await callback.answer()


@router.callback_query(F.data == "change_booking")
async def change_booking_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    language = await get_user_language(callback.from_user.id)
    await state.clear()
    await send_masters(callback.message, state, language)
    await callback.answer()


@router.callback_query(F.data == "back_to_masters")
async def back_to_masters_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    language = await get_user_language(callback.from_user.id)
    await send_masters(callback.message, state, language)
    await callback.answer()


@router.callback_query(F.data == "back_to_gender")
async def back_to_gender_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    language = await get_user_language(callback.from_user.id)
    await send_gender_choice(callback.message, state, language)
    await callback.answer()


@router.callback_query(F.data == "back_to_services")
async def back_to_services_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    language = await get_user_language(callback.from_user.id)
    await send_service_checklist(callback.message, state, language)
    await callback.answer()


@router.callback_query(F.data == "back_to_dates")
async def back_to_dates_handler(callback: CallbackQuery, state: FSMContext):
    if await stop_blocked_callback(callback):
        return

    language = await get_user_language(callback.from_user.id)
    await send_calendar(callback.message, state, language)
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def back_main_handler(callback: CallbackQuery, state: FSMContext):
    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)
    await state.clear()
    await callback.message.answer(texts["main_menu"], reply_markup=main_menu(language))
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("legacy_category:"))
async def legacy_category_handler(callback: CallbackQuery, state: FSMContext):
    # Тимчасова сумісність зі старим profile.py: переводимо користувача
    # на новий вибір Жіночі / Чоловічі.
    language = await get_user_language(callback.from_user.id)
    await send_gender_choice(callback.message, state, language)
    await callback.answer()
