import calendar
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from database.queries import (
    cancel_client_booking,
    get_active_bookings_by_telegram_id,
    get_booking_by_id,
    get_booking_selected_services,
    get_master_by_id,
    get_user_by_telegram_id,
    reschedule_client_booking,
    update_booking_calendar_events,
)
from handlers.user.booking import (
    date_has_available_time,
    get_available_times,
)
from keyboards.menus import main_menu
from locales.pt import BUTTONS as PT_BUTTONS
from locales.pt import TEXTS as PT_TEXTS
from locales.ua import BUTTONS as UA_BUTTONS
from locales.ua import TEXTS as UA_TEXTS
from services.calendar import (
    create_calendar_event,
    delete_calendar_event,
)
from states.my_bookings_state import MyBookingsState

router = Router()

LISBON_TZ = ZoneInfo("Europe/Lisbon")

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


def format_duration(minutes: int, language: str) -> str:
    minutes = int(minutes or 0)
    hours, rest = divmod(minutes, 60)

    if language == "pt":
        if hours and rest:
            return f"{hours} h {rest} min"
        if hours:
            return f"{hours} h"
        return f"{rest} min"

    if hours and rest:
        return f"{hours} год {rest} хв"
    if hours:
        return f"{hours} год"
    return f"{rest} хв"


def can_change_booking(booking) -> bool:
    booking_dt = datetime.strptime(
        f"{booking['date']} {booking['time']}",
        "%Y-%m-%d %H:%M",
    ).replace(tzinfo=LISBON_TZ)

    now = datetime.now(LISBON_TZ)
    return booking_dt - now >= timedelta(hours=24)


def parse_calendar_events(raw_value):
    if not raw_value:
        return []

    try:
        parsed = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return []

    if isinstance(parsed, list):
        return parsed

    return []


async def get_services_text(booking_id: int, language: str) -> str:
    services = await get_booking_selected_services(booking_id)

    if not services:
        return "—"

    lines = []

    for service in services:
        name = (
            service["name_pt"]
            if language == "pt" and service.get("name_pt")
            else service["name_ua"]
        )
        lines.append(f"• {name}")

        for extra in service.get("extras", []):
            extra_name = (
                extra.get("name_pt")
                if language == "pt" and extra.get("name_pt")
                else extra.get("name_ua")
            )
            if extra_name:
                lines.append(f"  + {extra_name}")

    return "\n".join(lines)


def booking_actions_keyboard(
    booking_id: int,
    language: str,
    can_change: bool,
):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS
    keyboard = []

    if can_change:
        reschedule_text = "🔄 Alterar data/hora" if language == "pt" else "🔄 Перенести"
        cancel_text = (
            "❌ Cancelar marcação" if language == "pt" else "❌ Скасувати запис"
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=reschedule_text,
                    callback_data=f"reschedule_booking:{booking_id}",
                )
            ]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=cancel_text,
                    callback_data=f"cancel_booking:{booking_id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text=buttons["back"],
                callback_data="my_bookings_list",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def cancel_confirm_keyboard(booking_id: int, language: str):
    confirm_text = "✅ Sim, cancelar" if language == "pt" else "✅ Так, скасувати"
    back_text = "⬅️ Não cancelar" if language == "pt" else "⬅️ Не скасовувати"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=confirm_text,
                    callback_data=f"cancel_booking_confirm:{booking_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=back_text,
                    callback_data=f"my_booking:{booking_id}",
                )
            ],
        ]
    )


def reschedule_times_keyboard(times: list[str], language: str):
    keyboard = []

    for index in range(0, len(times), 3):
        row = [
            InlineKeyboardButton(
                text=time_value,
                callback_data=f"reschedule_time:{time_value}",
            )
            for time_value in times[index : index + 3]
        ]
        keyboard.append(row)

    back_text = (
        "⬅️ Voltar ao calendário" if language == "pt" else "⬅️ Назад до календаря"
    )
    keyboard.append(
        [
            InlineKeyboardButton(
                text=back_text,
                callback_data="reschedule_back_calendar",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def reschedule_confirm_keyboard(language: str):
    confirm_text = (
        "✅ Confirmar alteração" if language == "pt" else "✅ Підтвердити перенесення"
    )
    back_text = (
        "⬅️ Escolher outro horário" if language == "pt" else "⬅️ Обрати інший час"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=confirm_text,
                    callback_data="reschedule_confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    text=back_text,
                    callback_data="reschedule_back_calendar",
                )
            ],
        ]
    )


async def build_selected_services_for_booking(booking_id: int):
    services = await get_booking_selected_services(booking_id)

    return [
        {
            "master_id": service["master_id"],
            "service_id": service["service_id"],
            "extras": service.get("extras", []),
        }
        for service in services
    ]


async def reschedule_calendar_keyboard(
    master,
    selected_services,
    year: int,
    month: int,
    language: str,
):
    today = datetime.now(LISBON_TZ).date()
    first_allowed = today
    last_allowed = today + timedelta(days=60)

    month_title = MONTHS_PT[month] if language == "pt" else MONTHS_UA[month]

    keyboard = [
        [
            InlineKeyboardButton(
                text=f"📅 {month_title} {year}",
                callback_data="reschedule_noop",
            )
        ],
        [
            InlineKeyboardButton(text=day, callback_data="reschedule_noop")
            for day in (
                ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
                if language == "pt"
                else ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
            )
        ],
    ]

    month_matrix = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)

    for week in month_matrix:
        row = []

        for day_number in week:
            if day_number == 0:
                row.append(
                    InlineKeyboardButton(
                        text=" ",
                        callback_data="reschedule_noop",
                    )
                )
                continue

            current_date = date(year, month, day_number)

            if current_date < first_allowed or current_date > last_allowed:
                row.append(
                    InlineKeyboardButton(
                        text="·",
                        callback_data="reschedule_noop",
                    )
                )
                continue

            date_str = current_date.strftime("%Y-%m-%d")
            has_time = await date_has_available_time(
                master,
                selected_services,
                date_str,
            )

            if has_time:
                row.append(
                    InlineKeyboardButton(
                        text=str(day_number),
                        callback_data=f"reschedule_date:{date_str}",
                    )
                )
            else:
                row.append(
                    InlineKeyboardButton(
                        text=f"{day_number}×",
                        callback_data="reschedule_noop",
                    )
                )

        keyboard.append(row)

    current_month = date(year, month, 1)
    previous_month = (current_month - timedelta(days=1)).replace(day=1)

    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    nav_row = []

    if previous_month >= date(today.year, today.month, 1):
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=(
                    f"reschedule_month:"
                    f"{previous_month.year}:"
                    f"{previous_month.month}"
                ),
            )
        )

    nav_row.append(
        InlineKeyboardButton(
            text="•",
            callback_data="reschedule_noop",
        )
    )

    if next_month <= last_allowed.replace(day=1):
        nav_row.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=(
                    f"reschedule_month:" f"{next_month.year}:" f"{next_month.month}"
                ),
            )
        )

    keyboard.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def show_my_bookings(message: Message, telegram_id: int):
    language = await get_user_language(telegram_id)
    texts, buttons = get_texts_and_buttons(language)
    bookings = await get_active_bookings_by_telegram_id(telegram_id)

    if not bookings:
        await message.answer(
            texts["no_bookings"],
            reply_markup=main_menu(language),
        )
        return

    keyboard = []

    for booking in bookings:
        status_icon = "✅" if booking["status"] == "confirmed" else "⏳"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{status_icon} "
                        f"{booking['date']} · "
                        f"{booking['time']} · "
                        f"{booking['master_name']}"
                    ),
                    callback_data=f"my_booking:{booking['id']}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text=buttons["main_menu"],
                callback_data="my_bookings_main",
            )
        ]
    )

    await message.answer(
        texts["my_bookings"],
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )


async def show_booking_details(
    message: Message,
    booking_id: int,
    telegram_id: int,
):
    language = await get_user_language(telegram_id)
    bookings = await get_active_bookings_by_telegram_id(telegram_id)

    booking = next(
        (item for item in bookings if item["id"] == booking_id),
        None,
    )

    if not booking:
        text = (
            "Esta marcação já não está ativa."
            if language == "pt"
            else "Цей запис уже не активний."
        )
        await message.answer(text)
        return

    services_text = await get_services_text(booking_id, language)

    status_text = (
        "Confirmada ✅"
        if language == "pt" and booking["status"] == "confirmed"
        else (
            "A aguardar confirmação ⏳"
            if language == "pt"
            else (
                "Підтверджено ✅"
                if booking["status"] == "confirmed"
                else "Очікує підтвердження ⏳"
            )
        )
    )

    if language == "pt":
        text = (
            "📋 A sua marcação\n\n"
            f"👩 Profissional: {booking['master_name']}\n"
            f"💅 Serviços:\n{services_text}\n\n"
            f"📅 Data: {booking['date']}\n"
            f"🕒 Hora: {booking['time']}\n"
            f"⏳ Duração: {format_duration(booking['total_duration'], language)}\n"
            f"💶 Total: {booking['total_price']:g}€\n"
            f"📌 Estado: {status_text}"
        )
    else:
        text = (
            "📋 Ваш запис\n\n"
            f"👩 Майстер: {booking['master_name']}\n"
            f"💅 Процедури:\n{services_text}\n\n"
            f"📅 Дата: {booking['date']}\n"
            f"🕒 Час: {booking['time']}\n"
            f"⏳ Тривалість: {format_duration(booking['total_duration'], language)}\n"
            f"💶 Вартість: {booking['total_price']:g}€\n"
            f"📌 Статус: {status_text}"
        )

    change_allowed = can_change_booking(booking)

    if not change_allowed:
        text += (
            "\n\n⚠️ Faltam menos de 24 horas. Para alterar ou cancelar, contacte a profissional."
            if language == "pt"
            else "\n\n⚠️ До запису менше 24 годин. Для перенесення або скасування зв’яжіться з майстром."
        )

    await message.answer(
        text,
        reply_markup=booking_actions_keyboard(
            booking_id,
            language,
            change_allowed,
        ),
    )


@router.message(F.text.in_(["📋 Мої записи", "📋 As minhas marcações"]))
async def my_bookings_handler(message: Message, state: FSMContext):
    await state.clear()
    await show_my_bookings(message, message.from_user.id)


@router.callback_query(F.data == "my_bookings_list")
async def my_bookings_list_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_my_bookings(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("my_booking:"))
async def my_booking_details_handler(callback: CallbackQuery):
    booking_id = int(callback.data.split(":", 1)[1])

    await show_booking_details(
        callback.message,
        booking_id,
        callback.from_user.id,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_booking:"))
async def cancel_booking_handler(callback: CallbackQuery):
    booking_id = int(callback.data.split(":", 1)[1])
    language = await get_user_language(callback.from_user.id)

    bookings = await get_active_bookings_by_telegram_id(callback.from_user.id)
    booking = next(
        (item for item in bookings if item["id"] == booking_id),
        None,
    )

    if not booking:
        await callback.answer(
            "Запис не знайдено",
            show_alert=True,
        )
        return

    if not can_change_booking(booking):
        text = (
            "Faltam menos de 24 horas. Contacte a profissional."
            if language == "pt"
            else "До запису менше 24 годин. Зв’яжіться з майстром."
        )
        await callback.answer(text, show_alert=True)
        return

    text = (
        "Tem a certeza de que pretende cancelar esta marcação?"
        if language == "pt"
        else "Ви точно хочете скасувати цей запис?"
    )

    await callback.message.answer(
        text,
        reply_markup=cancel_confirm_keyboard(
            booking_id,
            language,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_booking_confirm:"))
async def cancel_booking_confirm_handler(callback: CallbackQuery, state: FSMContext):
    booking_id = int(callback.data.split(":", 1)[1])
    language = await get_user_language(callback.from_user.id)

    bookings = await get_active_bookings_by_telegram_id(callback.from_user.id)
    booking = next(
        (item for item in bookings if item["id"] == booking_id),
        None,
    )

    if not booking:
        await callback.answer(
            "Запис не знайдено",
            show_alert=True,
        )
        return

    if not can_change_booking(booking):
        text = (
            "Faltam menos de 24 horas. Contacte a profissional."
            if language == "pt"
            else "До запису менше 24 годин. Зв’яжіться з майстром."
        )
        await callback.answer(text, show_alert=True)
        return

    calendar_events = parse_calendar_events(
        booking["calendar_event_id"],
    )

    for event in calendar_events:
        calendar_id = event.get("calendar_id")
        event_id = event.get("event_id")

        if calendar_id and event_id:
            delete_calendar_event(
                calendar_id=calendar_id,
                event_id=event_id,
            )

    cancelled = await cancel_client_booking(
        booking_id=booking_id,
        telegram_id=callback.from_user.id,
    )

    if not cancelled:
        await callback.answer(
            "Не вдалося скасувати запис",
            show_alert=True,
        )
        return

    await state.clear()

    text = "✅ A marcação foi cancelada." if language == "pt" else "✅ Запис скасовано."
    await callback.message.answer(
        text,
        reply_markup=main_menu(language),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reschedule_booking:"))
async def reschedule_booking_handler(callback: CallbackQuery, state: FSMContext):
    booking_id = int(callback.data.split(":", 1)[1])
    language = await get_user_language(callback.from_user.id)

    bookings = await get_active_bookings_by_telegram_id(callback.from_user.id)
    booking = next(
        (item for item in bookings if item["id"] == booking_id),
        None,
    )

    if not booking:
        await callback.answer(
            "Запис не знайдено",
            show_alert=True,
        )
        return

    if not can_change_booking(booking):
        text = (
            "Faltam menos de 24 horas. Contacte a profissional."
            if language == "pt"
            else "До запису менше 24 годин. Зв’яжіться з майстром."
        )
        await callback.answer(text, show_alert=True)
        return

    selected_services = await build_selected_services_for_booking(
        booking_id,
    )

    if not selected_services:
        await callback.answer(
            "Не вдалося завантажити послуги запису",
            show_alert=True,
        )
        return

    master = await get_master_by_id(booking["master_id"])

    await state.clear()
    await state.update_data(
        reschedule_booking_id=booking_id,
        reschedule_master_id=booking["master_id"],
        reschedule_selected_services=selected_services,
        old_date=booking["date"],
        old_time=booking["time"],
        old_calendar_event_id=booking["calendar_event_id"],
    )
    await state.set_state(MyBookingsState.choosing_new_date)

    today = datetime.now(LISBON_TZ).date()

    text = "📅 Escolha a nova data:" if language == "pt" else "📅 Оберіть нову дату:"

    await callback.message.answer(
        text,
        reply_markup=await reschedule_calendar_keyboard(
            master=master,
            selected_services=selected_services,
            year=today.year,
            month=today.month,
            language=language,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reschedule_month:"))
async def reschedule_month_handler(callback: CallbackQuery, state: FSMContext):
    _, year, month = callback.data.split(":")
    language = await get_user_language(callback.from_user.id)
    data = await state.get_data()

    master = await get_master_by_id(
        data["reschedule_master_id"],
    )

    await callback.message.edit_reply_markup(
        reply_markup=await reschedule_calendar_keyboard(
            master=master,
            selected_services=data["reschedule_selected_services"],
            year=int(year),
            month=int(month),
            language=language,
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reschedule_date:"))
async def reschedule_date_handler(callback: CallbackQuery, state: FSMContext):
    new_date = callback.data.split(":", 1)[1]
    language = await get_user_language(callback.from_user.id)
    data = await state.get_data()

    master = await get_master_by_id(
        data["reschedule_master_id"],
    )

    times = await get_available_times(
        master,
        data["reschedule_selected_services"],
        new_date,
    )

    if not times:
        text = (
            "Já não existem horários livres neste dia."
            if language == "pt"
            else "На цей день вільних годин уже немає."
        )
        await callback.answer(text, show_alert=True)
        return

    await state.update_data(reschedule_new_date=new_date)
    await state.set_state(MyBookingsState.choosing_new_time)

    text = "🕒 Escolha a nova hora:" if language == "pt" else "🕒 Оберіть новий час:"

    await callback.message.answer(
        text,
        reply_markup=reschedule_times_keyboard(
            times,
            language,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reschedule_time:"))
async def reschedule_time_handler(callback: CallbackQuery, state: FSMContext):
    new_time = callback.data.split(":", 1)[1]
    language = await get_user_language(callback.from_user.id)
    data = await state.get_data()

    await state.update_data(reschedule_new_time=new_time)
    await state.set_state(MyBookingsState.confirming_reschedule)

    text = (
        "✅ Confirme a alteração:\n\n"
        f"📅 Nova data: {data['reschedule_new_date']}\n"
        f"🕒 Nova hora: {new_time}"
        if language == "pt"
        else "✅ Підтвердіть перенесення:\n\n"
        f"📅 Нова дата: {data['reschedule_new_date']}\n"
        f"🕒 Новий час: {new_time}"
    )

    await callback.message.answer(
        text,
        reply_markup=reschedule_confirm_keyboard(language),
    )
    await callback.answer()


@router.callback_query(F.data == "reschedule_confirm")
async def reschedule_confirm_handler(callback: CallbackQuery, state: FSMContext):
    language = await get_user_language(callback.from_user.id)
    data = await state.get_data()

    booking_id = data["reschedule_booking_id"]
    new_date = data["reschedule_new_date"]
    new_time = data["reschedule_new_time"]
    selected_services = data["reschedule_selected_services"]

    master = await get_master_by_id(
        data["reschedule_master_id"],
    )

    available_times = await get_available_times(
        master,
        selected_services,
        new_date,
    )

    if new_time not in available_times:
        text = (
            "Este horário já não está disponível. Escolha outro."
            if language == "pt"
            else "Цей час уже зайнятий. Оберіть інший."
        )
        await callback.answer(text, show_alert=True)
        return

    old_calendar_events = parse_calendar_events(
        data.get("old_calendar_event_id"),
    )

    for event in old_calendar_events:
        calendar_id = event.get("calendar_id")
        event_id = event.get("event_id")

        if calendar_id and event_id:
            delete_calendar_event(
                calendar_id=calendar_id,
                event_id=event_id,
            )

    changed = await reschedule_client_booking(
        booking_id=booking_id,
        telegram_id=callback.from_user.id,
        new_date=new_date,
        new_time=new_time,
    )

    if not changed:
        await callback.answer(
            "Не вдалося перенести запис",
            show_alert=True,
        )
        return

    booking = await get_booking_by_id(booking_id)
    services = await get_booking_selected_services(booking_id)
    calendar_events = []

    for service in services:
        service_master = await get_master_by_id(
            service["master_id"],
        )

        if not service_master or not service_master["calendar_id"]:
            continue

        service_name = (
            service["name_pt"]
            if language == "pt" and service.get("name_pt")
            else service["name_ua"]
        )

        try:
            event = create_calendar_event(
                calendar_id=service_master["calendar_id"],
                client_name=booking["client_name"],
                client_phone=booking["client_phone"],
                service_name=service_name,
                master_name=service_master["name"],
                date=service["date"],
                time=service["start_time"],
                duration=service["duration"],
            )

            event_id = event.get("id")

            if event_id:
                calendar_events.append(
                    {
                        "calendar_id": service_master["calendar_id"],
                        "event_id": event_id,
                    }
                )
        except Exception as error:
            print("RESCHEDULE GOOGLE CALENDAR ERROR:", error)

    await update_booking_calendar_events(
        booking_id,
        calendar_events,
    )

    await state.clear()

    text = (
        "✅ A marcação foi alterada com sucesso.\n\n"
        f"📅 {new_date}\n"
        f"🕒 {new_time}"
        if language == "pt"
        else "✅ Запис успішно перенесено.\n\n" f"📅 {new_date}\n" f"🕒 {new_time}"
    )

    await callback.message.answer(
        text,
        reply_markup=main_menu(language),
    )
    await callback.answer()


@router.callback_query(F.data == "reschedule_back_calendar")
async def reschedule_back_calendar_handler(callback: CallbackQuery, state: FSMContext):
    language = await get_user_language(callback.from_user.id)
    data = await state.get_data()

    master = await get_master_by_id(
        data["reschedule_master_id"],
    )
    today = datetime.now(LISBON_TZ).date()

    await state.set_state(MyBookingsState.choosing_new_date)

    text = "📅 Escolha a nova data:" if language == "pt" else "📅 Оберіть нову дату:"

    await callback.message.answer(
        text,
        reply_markup=await reschedule_calendar_keyboard(
            master=master,
            selected_services=data["reschedule_selected_services"],
            year=today.year,
            month=today.month,
            language=language,
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "reschedule_noop")
async def reschedule_noop_handler(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "my_bookings_main")
async def my_bookings_main_handler(callback: CallbackQuery, state: FSMContext):
    language = await get_user_language(callback.from_user.id)
    texts, _ = get_texts_and_buttons(language)

    await state.clear()
    await callback.message.answer(
        texts["main_menu"],
        reply_markup=main_menu(language),
    )
    await callback.answer()
