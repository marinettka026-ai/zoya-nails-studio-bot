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

    if language == "pt":
        title = f"💅 Serviços — {master['name']}"
    else:
        title = f"💅 Послуги — {master['name']}"

    lines = [title, ""]

    for service in services:
        name = (
            service["name_pt"]
            if language == "pt" and service["name_pt"]
            else service["name_ua"]
        )

        description = (
            service["description_pt"]
            if language == "pt" and service["description_pt"]
            else service["description_ua"]
        )

        lines.append(f"✨ {name}")

        if description:
            lines.append(description)

        lines.append(f"💶 {format_price(service['price'])} €")
        lines.append(f"⏳ {format_duration(service['duration'], language)}")
        lines.append("")

    if extras:
        lines.append(
            "➕ Serviços adicionais" if language == "pt" else "➕ Додаткові послуги"
        )
        lines.append("")

        for extra in extras:
            name = (
                extra["name_pt"]
                if language == "pt" and extra["name_pt"]
                else extra["name_ua"]
            )

            lines.append(f"✨ {name}")
            lines.append(f"💶 {format_extra_price(extra['price'], language)}")

            if int(extra["duration"] or 0) > 0:
                duration_text = format_duration(
                    extra["duration"],
                    language,
                )

                if language == "pt":
                    lines.append(f"⏳ +{duration_text}")
                else:
                    lines.append(f"⏳ +{duration_text}")

            lines.append("")

    await callback.message.answer(
        "\n".join(lines),
        reply_markup=public_service_back_to_masters_keyboard(language),
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
