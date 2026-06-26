from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from database.queries import (
    add_user,
    update_user_language,
    get_user_by_telegram_id,
    get_all_services,
)

from keyboards.menus import language_menu, main_menu

from locales.ua import TEXTS as UA_TEXTS
from locales.ua import BUTTONS as UA_BUTTONS

from locales.pt import TEXTS as PT_TEXTS
from locales.pt import BUTTONS as PT_BUTTONS

router = Router()


def public_service_categories_keyboard(language: str = "ua"):
    if language == "pt":
        categories = [
            ("💅 Manicure feminina", "wm"),
            ("👣 Pedicure feminina", "wp"),
            ("🧔 Manicure e pedicure masculina", "ms"),
        ]
        back_text = PT_BUTTONS["back"]
    else:
        categories = [
            ("💅 Манікюр жіночий", "wm"),
            ("👣 Педикюр жіночий", "wp"),
            ("🧔 Чоловічий манікюр та педикюр", "ms"),
        ]
        back_text = UA_BUTTONS["back"]

    keyboard = []

    for title, category_key in categories:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=title,
                    callback_data=f"public_services_cat:{category_key}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text=back_text,
                callback_data=f"public_services_back:{language}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def format_duration(duration: int, language: str = "ua"):
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

    await message.answer(UA_TEXTS["choose_language"], reply_markup=language_menu())


@router.message(F.text == UA_BUTTONS["ua"])
async def choose_ua(message: Message):
    await update_user_language(message.from_user.id, "ua")

    await message.answer(UA_TEXTS["main_menu"], reply_markup=main_menu("ua"))


@router.message(F.text == UA_BUTTONS["pt"])
async def choose_pt(message: Message):
    await update_user_language(message.from_user.id, "pt")

    await message.answer(PT_TEXTS["main_menu"], reply_markup=main_menu("pt"))


@router.message(F.text == UA_BUTTONS["main_menu"])
async def ua_main_menu(message: Message):
    await message.answer(UA_TEXTS["main_menu"], reply_markup=main_menu("ua"))


@router.message(F.text == PT_BUTTONS["main_menu"])
async def pt_main_menu(message: Message):
    await message.answer(PT_TEXTS["main_menu"], reply_markup=main_menu("pt"))


@router.message(F.text.in_([UA_BUTTONS["services"], PT_BUTTONS["services"]]))
async def public_services_handler(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    language = user["language"] if user and user["language"] else "ua"

    text = (
        "💅 Оберіть категорію послуг:"
        if language == "ua"
        else "💅 Escolha uma categoria de serviços:"
    )

    await message.answer(
        text,
        reply_markup=public_service_categories_keyboard(language),
    )


@router.callback_query(F.data.startswith("public_services_cat:"))
async def public_services_category_handler(callback: CallbackQuery):
    category_key = callback.data.split(":", 1)[1]

    categories_map = {
        "wm": "Манікюр жіночий",
        "wp": "Педикюр жіночий",
        "ms": "Чоловічий манікюр та педикюр",
    }

    category_ua = categories_map.get(category_key)

    if not category_ua:
        await callback.answer("Категорію не знайдено", show_alert=True)
        return

    user = await get_user_by_telegram_id(callback.from_user.id)
    language = user["language"] if user and user["language"] else "ua"

    services = await get_all_services()

    filtered_services = [
        service for service in services if service["category_ua"] == category_ua
    ]

    if not filtered_services:
        text = (
            "У цій категорії поки що немає послуг."
            if language == "ua"
            else "Ainda não há serviços nesta categoria."
        )
        await callback.message.answer(text)
        await callback.answer()
        return

    title = "💅 Serviços:" if language == "pt" else "💅 Послуги:"
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

    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data.startswith("public_services_back:"))
async def public_services_back_handler(callback: CallbackQuery):
    language = callback.data.split(":")[1]
    texts = PT_TEXTS if language == "pt" else UA_TEXTS

    await callback.message.answer(
        texts["main_menu"],
        reply_markup=main_menu(language),
    )

    await callback.answer()
