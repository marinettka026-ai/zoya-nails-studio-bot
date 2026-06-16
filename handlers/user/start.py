from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from database.queries import add_user, update_user_language, get_user_by_telegram_id

from keyboards.menus import language_menu, main_menu

from locales.ua import TEXTS as UA_TEXTS
from locales.ua import BUTTONS as UA_BUTTONS

from locales.pt import TEXTS as PT_TEXTS
from locales.pt import BUTTONS as PT_BUTTONS

router = Router()


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
