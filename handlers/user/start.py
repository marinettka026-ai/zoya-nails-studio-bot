import html

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from database.queries import (
    add_user,
    get_active_masters,
    get_master_by_id,
    get_service_extras_by_category,
    get_services_by_master,
    get_user_by_telegram_id,
    update_user_language,
)
from keyboards.menus import language_menu, main_menu
from locales.pt import BUTTONS as PT_BUTTONS
from locales.pt import TEXTS as PT_TEXTS
from locales.ua import BUTTONS as UA_BUTTONS
from locales.ua import TEXTS as UA_TEXTS

router = Router()


EXTRA_CATEGORIES = [
    "Манікюр жіночий",
    "Педикюр жіночий",
    "Чоловічий манікюр та педикюр",
]


def public_service_masters_keyboard(masters, language: str = "ua"):
    back_text = PT_BUTTONS["back"] if language == "pt" else UA_BUTTONS["back"]

    keyboard = []

    for master in masters:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🌸 {master['name']}",
                    callback_data=f"public_services_master:{master['id']}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text=back_text,
                callback_data="public_services_back",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def public_service_back_to_masters_keyboard(language: str = "ua"):
    if language == "pt":
        back_text = "⬅️ Aos profissionais"
    else:
        back_text = "⬅️ До майстрів"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=back_text,
                    callback_data="public_services_choose_master",
                )
            ]
        ]
    )


def format_duration(duration: int, language: str = "ua"):
    duration = int(duration or 0)
    hours = duration // 60
    minutes = duration % 60

    if language == "pt":
        if hours and minutes:
            return f"{hours} h {minutes} min"
        if hours:
            return f"{hours} h"
        return f"{minutes} min"

    if hours and minutes:
        return f"{hours} год {minutes} хв"
    if hours:
        return f"{hours} год"
    return f"{minutes} хв"


def format_price(price) -> str:
    value = float(price or 0)

    if value.is_integer():
        return str(int(value))

    return f"{value:.2f}".rstrip("0").rstrip(".")


def format_extra_price(price, language: str = "ua") -> str:
    value = float(price or 0)

    if value == 0:
        return "Grátis" if language == "pt" else "Безкоштовно"

    return f"+{format_price(value)} €"


async def get_master_extras(master_id: int):
    extras = []

    for category_ua in EXTRA_CATEGORIES:
        category_extras = await get_service_extras_by_category(
            master_id,
            category_ua,
        )
        extras.extend(category_extras)

    return extras


def service_group(service) -> str:
    category = (service["category_ua"] or "").lower()
    name = (service["name_ua"] or "").lower()

    if "чолов" in category or "чолов" in name:
        return "male"

    if "педик" in category or "педик" in name:
        return "pedicure"

    return "manicure"


def compact_service_name(service, language: str = "ua") -> str:
    name = (
        service["name_pt"]
        if language == "pt" and service["name_pt"]
        else service["name_ua"]
    )

    group = service_group(service)
    normalized = (name or "").strip().lower()

    if group == "male":
        if "педик" in normalized or "pedicure" in normalized:
            return "Pedicure" if language == "pt" else "Педикюр"
        if "манік" in normalized or "manicure" in normalized:
            return "Manicure" if language == "pt" else "Манікюр"

    return name


def public_price_note(language: str = "ua") -> str:
    if language == "pt":
        return (
            "<b>ℹ️ IMPORTANTE</b>\n\n"
            "A remoção do revestimento e a reparação de algumas unhas "
            "dentro do serviço completo não são cobradas à parte.\n\n"
            "Na manicure com verniz gel, dependendo do comprimento das unhas, "
            "pode ser acrescentado +5 €."
        )

    return (
        "<b>ℹ️ ВАЖЛИВО</b>\n\n"
        "Зняття покриття та ремонт декількох нігтів у комплексній послузі "
        "додатково не оплачуються.\n\n"
        "Для манікюру з гель-лаком залежно від довжини нігтів "
        "може бути додано +5 €."
    )


def extra_display_duration(extra, language: str = "ua") -> str:
    name_ua = (extra["name_ua"] or "").strip().lower()

    if "дизайн на всі нігті" in name_ua:
        return "15–30 min" if language == "pt" else "15–30 хв"

    if "spa" in name_ua:
        return "15–20 min" if language == "pt" else "15–20 хв"

    return format_duration(extra["duration"], language)


@router.message(CommandStart())
async def start_handler(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)

    if not user:
        await add_user(
            telegram_id=message.from_user.id,
            name=message.from_user.full_name,
            role="client",
        )

    await message.answer(
        UA_TEXTS["choose_language"],
        reply_markup=language_menu(),
    )


@router.message(F.text == UA_BUTTONS["ua"])
async def choose_ua(message: Message):
    await update_user_language(message.from_user.id, "ua")
    await message.answer(
        UA_TEXTS["main_menu"],
        reply_markup=main_menu("ua"),
    )


@router.message(F.text == UA_BUTTONS["pt"])
async def choose_pt(message: Message):
    await update_user_language(message.from_user.id, "pt")
    await message.answer(
        PT_TEXTS["main_menu"],
        reply_markup=main_menu("pt"),
    )


@router.message(F.text == UA_BUTTONS["main_menu"])
async def ua_main_menu(message: Message):
    await message.answer(
        UA_TEXTS["main_menu"],
        reply_markup=main_menu("ua"),
    )


@router.message(F.text == PT_BUTTONS["main_menu"])
async def pt_main_menu(message: Message):
    await message.answer(
        PT_TEXTS["main_menu"],
        reply_markup=main_menu("pt"),
    )


@router.message(
    F.text.in_(
        [
            UA_BUTTONS["services"],
            PT_BUTTONS["services"],
        ]
    )
)
async def public_services_handler(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    language = user["language"] if user and user["language"] else "ua"

    masters = await get_active_masters()

    if not masters:
        text = (
            "Поки що немає доступних майстрів."
            if language == "ua"
            else "Ainda não há profissionais disponíveis."
        )
        await message.answer(text)
        return

    text = (
        "💅 Послуги\n\nОберіть майстра, щоб переглянути актуальний прайс:"
        if language == "ua"
        else "💅 Serviços\n\nEscolha o profissional para ver os preços atuais:"
    )

    await message.answer(
        text,
        reply_markup=public_service_masters_keyboard(
            masters,
            language,
        ),
    )


@router.callback_query(F.data == "public_services_choose_master")
async def public_services_choose_master_handler(callback: CallbackQuery):
    user = await get_user_by_telegram_id(callback.from_user.id)
    language = user["language"] if user and user["language"] else "ua"

    masters = await get_active_masters()

    if not masters:
        text = (
            "Поки що немає доступних майстрів."
            if language == "ua"
            else "Ainda não há profissionais disponíveis."
        )
        await callback.message.answer(text)
        await callback.answer()
        return

    text = (
        "💅 Послуги\n\nОберіть майстра, щоб переглянути актуальний прайс:"
        if language == "ua"
        else "💅 Serviços\n\nEscolha o profissional para ver os preços atuais:"
    )

    await callback.message.answer(
        text,
        reply_markup=public_service_masters_keyboard(
            masters,
            language,
        ),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("public_services_master:"))
async def public_services_master_handler(callback: CallbackQuery):
    master_id = int(callback.data.split(":", 1)[1])

    user = await get_user_by_telegram_id(callback.from_user.id)
    language = user["language"] if user and user["language"] else "ua"

    master = await get_master_by_id(master_id)

    if not master or not master["is_active"]:
        text = (
            "Цей майстер зараз недоступний."
            if language == "ua"
            else "Este profissional não está disponível no momento."
        )
        await callback.message.answer(text)
        await callback.answer()
        return

    services = await get_services_by_master(master_id)
    extras = await get_master_extras(master_id)

    if not services:
        text = (
            f"У {master['name']} поки що немає доступних послуг."
            if language == "ua"
            else f"{master['name']} ainda não tem serviços disponíveis."
        )

        await callback.message.answer(
            text,
            reply_markup=public_service_back_to_masters_keyboard(language),
        )
        await callback.answer()
        return

    master_name = html.escape(str(master["name"]))

    if language == "pt":
        lines = [f"<b>💅 SERVIÇOS — {master_name.upper()}</b>", ""]
        group_titles = {
            "manicure": "<b>🌸 MANICURE</b>",
            "pedicure": "<b>🦶 PEDICURE</b>",
            "male": "<b>👨 SERVIÇOS MASCULINOS</b>",
        }
    else:
        lines = [f"<b>💅 ПОСЛУГИ — {master_name.upper()}</b>", ""]
        group_titles = {
            "manicure": "<b>🌸 МАНІКЮР</b>",
            "pedicure": "<b>🦶 ПЕДИКЮР</b>",
            "male": "<b>👨 ЧОЛОВІЧІ ПОСЛУГИ</b>",
        }

    grouped_services = {
        "manicure": [],
        "pedicure": [],
        "male": [],
    }

    for service in services:
        grouped_services[service_group(service)].append(service)

    for group_name in ("manicure", "pedicure", "male"):
        group_services = grouped_services[group_name]

        if not group_services:
            continue

        lines.append(group_titles[group_name])
        lines.append("")

        for service in group_services:
            name = compact_service_name(service, language)
            safe_name = html.escape(str(name))

            lines.append(f"✨ <b>{safe_name}</b>")
            lines.append(
                f"{format_price(service['price'])} € • "
                f"{format_duration(service['duration'], language)}"
            )
            lines.append("")

    if extras:
        lines.append(
            "<b>➕ SERVIÇOS ADICIONAIS</b>"
            if language == "pt"
            else "<b>➕ ДОДАТКОВІ ПОСЛУГИ</b>"
        )
        lines.append("")

        seen_extra_names = set()

        for extra in extras:
            name = (
                extra["name_pt"]
                if language == "pt" and extra["name_pt"]
                else extra["name_ua"]
            )

            # In the public price list, show Baehr SPA only once.
            normalized_name = (extra["name_ua"] or "").strip().lower()
            dedupe_key = (
                "baehr_spa"
                if "spa" in normalized_name and "baehr" in normalized_name
                else normalized_name
            )

            if dedupe_key in seen_extra_names:
                continue

            seen_extra_names.add(dedupe_key)

            safe_name = html.escape(str(name))
            price_text = format_extra_price(extra["price"], language)

            if int(extra["duration"] or 0) > 0:
                duration_text = extra_display_duration(extra, language)
                lines.append(f"✨ {safe_name} — {price_text} • +{duration_text}")
            else:
                lines.append(f"✨ {safe_name} — {price_text}")

        lines.append("")
        lines.append("")
        lines.append(public_price_note(language))

    await callback.message.answer(
        "\n".join(lines),
        reply_markup=public_service_back_to_masters_keyboard(language),
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "public_services_back")
async def public_services_back_handler(callback: CallbackQuery):
    user = await get_user_by_telegram_id(callback.from_user.id)
    language = user["language"] if user and user["language"] else "ua"
    texts = PT_TEXTS if language == "pt" else UA_TEXTS

    await callback.message.answer(
        texts["main_menu"],
        reply_markup=main_menu(language),
    )

    await callback.answer()
