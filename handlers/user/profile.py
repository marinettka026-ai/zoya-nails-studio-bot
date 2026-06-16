from aiogram import Router, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.fsm.context import FSMContext

from database.queries import (
    get_user_by_telegram_id,
    get_active_masters,
    get_all_services,
    get_service_categories_by_master,
)

from keyboards.menus import main_menu

from locales.ua import BUTTONS as UA_BUTTONS, TEXTS as UA_TEXTS
from locales.pt import BUTTONS as PT_BUTTONS, TEXTS as PT_TEXTS

from states.booking_state import BookingState

from handlers.user.booking import (
    service_categories_keyboard,
)

router = Router()


router = Router()

MAP_URL = "https://maps.google.com/?q=38.699711,-9.427149"
INSTAGRAM_URL = "https://www.instagram.com/zoya_nails_studio?igsh=MTJqMHlpamxqanU0OQ%3D%3D&utm_source=qr"


async def get_user_language(telegram_id: int) -> str:
    user = await get_user_by_telegram_id(telegram_id)

    if user and user["language"]:
        return user["language"]

    return "ua"


def contacts_keyboard(language: str = "ua"):
    map_text = "🗺 Abrir no mapa" if language == "pt" else "🗺 Відкрити на карті"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=map_text, url=MAP_URL)],
            [InlineKeyboardButton(text="📷 Instagram", url=INSTAGRAM_URL)],
        ]
    )


def masters_list_keyboard(masters, language: str = "ua"):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS
    keyboard = []

    for master in masters:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🌸 {master['name']}",
                    callback_data=f"profile_master:{master['id']}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text=buttons["main_menu"],
                callback_data="profile_main_menu",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def master_card_keyboard(master_id: int, language: str = "ua"):
    buttons = PT_BUTTONS if language == "pt" else UA_BUTTONS

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=buttons["book_master"],
                    callback_data=f"profile_book_master:{master_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=buttons["back_to_masters"],
                    callback_data="profile_back_to_masters",
                )
            ],
            [
                InlineKeyboardButton(
                    text=buttons["main_menu"],
                    callback_data="profile_main_menu",
                )
            ],
        ]
    )


def services_text(services, language: str = "ua"):
    if not services:
        return (
            "Поки що послуги не додані."
            if language == "ua"
            else "Ainda não há serviços adicionados."
        )

    grouped = {}

    for service in services:
        category = (
            service["category_pt"]
            if language == "pt" and service["category_pt"]
            else service["category_ua"]
        )

        name = (
            service["name_pt"]
            if language == "pt" and service["name_pt"]
            else service["name_ua"]
        )

        service_data = dict(service)
        service_data["display_name"] = name
        grouped.setdefault(category, []).append(service_data)

    if language == "pt":
        text = "💅 Serviços e preços\n\n"
    else:
        text = "💅 Послуги та прайс\n\n"

    for category, items in grouped.items():
        text += f"✨ {category}\n"

        for item in items:
            description = (
                item["description_pt"]
                if language == "pt" and item["description_pt"]
                else item["description_ua"]
            )

            text += (
                f"• {item['display_name']}\n"
                f"  💶 {item['price']}€ · ⏳ {item['duration']} хв\n"
            )

            if description:
                text += f"  {description}\n"

            text += "\n"

    return text


@router.message(F.text.in_([UA_BUTTONS["main_menu"], PT_BUTTONS["main_menu"]]))
async def back_to_main_menu(message: Message):
    language = await get_user_language(message.from_user.id)

    if language == "pt":
        await message.answer(PT_TEXTS["main_menu"], reply_markup=main_menu("pt"))
    else:
        await message.answer(UA_TEXTS["main_menu"], reply_markup=main_menu("ua"))


@router.message(F.text.in_([UA_BUTTONS["contacts"], PT_BUTTONS["contacts"]]))
async def contacts_handler(message: Message):
    language = await get_user_language(message.from_user.id)

    if language == "pt":
        await message.answer(
            PT_TEXTS["contacts"],
            reply_markup=contacts_keyboard("pt"),
        )
    else:
        await message.answer(
            UA_TEXTS["contacts"],
            reply_markup=contacts_keyboard("ua"),
        )


@router.message(F.text.in_([UA_BUTTONS["services"], PT_BUTTONS["services"]]))
async def services_handler(message: Message):
    language = await get_user_language(message.from_user.id)

    services = await get_all_services()

    await message.answer(
        services_text(services, language),
        reply_markup=main_menu(language),
    )


@router.message(F.text.in_([UA_BUTTONS["masters"], PT_BUTTONS["masters"]]))
async def masters_handler(message: Message):
    language = await get_user_language(message.from_user.id)
    texts = PT_TEXTS if language == "pt" else UA_TEXTS

    masters = await get_active_masters()

    if not masters:
        await message.answer(
            "Поки що майстрів немає."
            if language == "ua"
            else "Ainda não há profissionais adicionadas."
        )
        return

    await message.answer(
        texts["masters"],
        reply_markup=masters_list_keyboard(masters, language),
    )


@router.callback_query(F.data.startswith("profile_master:"))
async def profile_master_card(callback: CallbackQuery):
    from database.queries import get_master_by_id

    master_id = int(callback.data.split(":")[1])
    language = await get_user_language(callback.from_user.id)

    master = await get_master_by_id(master_id)

    if not master:
        await callback.answer("Майстра не знайдено", show_alert=True)
        return

    description = (
        master["description_pt"]
        if language == "pt" and master["description_pt"]
        else master["description_ua"]
    )

    text = f"🌸 {master['name']}\n\n{description}"

    if master["photo_id"]:
        await callback.message.answer_photo(
            photo=master["photo_id"],
            caption=text,
            reply_markup=master_card_keyboard(master_id, language),
        )
    else:
        await callback.message.answer(
            text,
            reply_markup=master_card_keyboard(master_id, language),
        )

    await callback.answer()


@router.callback_query(F.data == "profile_back_to_masters")
async def profile_back_to_masters(callback: CallbackQuery):
    language = await get_user_language(callback.from_user.id)
    texts = PT_TEXTS if language == "pt" else UA_TEXTS

    masters = await get_active_masters()

    await callback.message.answer(
        texts["masters"],
        reply_markup=masters_list_keyboard(masters, language),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("profile_book_master:"))
async def profile_book_master(callback: CallbackQuery, state: FSMContext):
    user = await get_user_by_telegram_id(callback.from_user.id)

    if user and user["is_blocked"]:
        await callback.message.answer(
            "⛔ Запис через бота для вас недоступний.\n\n"
            "Будь ласка, зв’яжіться з майстром напряму."
        )
        await callback.answer()
        return

    master_id = int(callback.data.split(":")[1])

    language = await get_user_language(callback.from_user.id)

    categories = await get_service_categories_by_master(master_id)

    if not categories:
        await callback.answer(
            "У майстра поки немає послуг",
            show_alert=True,
        )
        return

    await state.update_data(master_id=master_id)
    await state.set_state(BookingState.choosing_category)

    if language == "pt":
        text = "💅 Escolha uma categoria:"
    else:
        text = "💅 Оберіть категорію послуги:"

    await callback.message.answer(
        text,
        reply_markup=service_categories_keyboard(categories, language),
    )

    await callback.answer()


@router.callback_query(F.data == "profile_main_menu")
async def profile_main_menu(callback: CallbackQuery):
    language = await get_user_language(callback.from_user.id)

    if language == "pt":
        await callback.message.answer(
            PT_TEXTS["main_menu"],
            reply_markup=main_menu("pt"),
        )
    else:
        await callback.message.answer(
            UA_TEXTS["main_menu"],
            reply_markup=main_menu("ua"),
        )

    await callback.answer()
