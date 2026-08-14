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
    get_all_services,
    get_user_by_telegram_id,
    update_user_language,
)
from keyboards.menus import language_menu, main_menu
from locales.pt import BUTTONS as PT_BUTTONS
from locales.pt import TEXTS as PT_TEXTS
from locales.ua import BUTTONS as UA_BUTTONS
from locales.ua import TEXTS as UA_TEXTS

router = Router()


def public_service_gender_keyboard(language: str = "ua"):
    if language == "pt":
        female_text = "👩 Serviços femininos"
        male_text = "👨 Serviços masculinos"
        back_text = PT_BUTTONS["back"]
    else:
        female_text = "👩 Жіночі послуги"
        male_text = "👨 Чоловічі послуги"
        back_text = UA_BUTTONS["back"]

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=female_text,
                    callback_data="public_services_gender:female",
                )
            ],
            [
                InlineKeyboardButton(
                    text=male_text,
                    callback_data="public_services_gender:male",
                )
            ],
            [
                InlineKeyboardButton(
                    text=back_text,
                    callback_data="public_services_back",
                )
            ],
        ]
    )


def is_male_service(service) -> bool:
    text = " ".join(
        str(value or "").lower()
        for value in (
            service["category_ua"],
            service["category_pt"],
            service["name_ua"],
            service["name_pt"],
        )
    )

    markers = (
        "чолов",
        "муж",
        "mascul",
        "homem",
    )

    return any(marker in text for marker in markers)


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


@router.message(F.text.in_([UA_BUTTONS["services"], PT_BUTTONS["services"]]))
async def public_services_handler(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    language = user["language"] if user and user["language"] else "ua"

    text = "💅 Оберіть послуги:" if language == "ua" else "💅 Escolha os serviços:"

    await message.answer(
        text,
        reply_markup=public_service_gender_keyboard(language),
    )


@router.callback_query(F.data.startswith("public_services_gender:"))
async def public_services_gender_handler(callback: CallbackQuery):
    gender = callback.data.split(":", 1)[1]

    if gender not in {"female", "male"}:
        await callback.answer("Категорію не знайдено", show_alert=True)
        return

    user = await get_user_by_telegram_id(callback.from_user.id)
    language = user["language"] if user and user["language"] else "ua"

    services = await get_all_services()

    if gender == "male":
        filtered_services = [
            service for service in services if is_male_service(service)
        ]
    else:
        filtered_services = [
            service for service in services if not is_male_service(service)
        ]

    if not filtered_services:
        text = (
            "У цій категорії поки що немає послуг."
            if language == "ua"
            else "Ainda não há serviços nesta categoria."
        )
        await callback.message.answer(
            text,
            reply_markup=public_service_gender_keyboard(language),
        )
        await callback.answer()
        return

    if language == "pt":
        title = (
            "👨 Serviços masculinos:" if gender == "male" else "👩 Serviços femininos:"
        )
    else:
        title = "👨 Чоловічі послуги:" if gender == "male" else "👩 Жіночі послуги:"

    lines = [title, ""]

    for service in filtered_services:
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

        lines.append(f"💶 {service['price']}€")
        lines.append(f"⏳ {format_duration(service['duration'], language)}")
        lines.append("")

    await callback.message.answer(
        "\n".join(lines),
        reply_markup=public_service_gender_keyboard(language),
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
