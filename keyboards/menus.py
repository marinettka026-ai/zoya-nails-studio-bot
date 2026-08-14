from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from locales.ua import BUTTONS as UA
from locales.pt import BUTTONS as PT


def language_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=UA["ua"]),
                KeyboardButton(text=UA["pt"]),
            ]
        ],
        resize_keyboard=True,
    )


def main_menu(language: str = "ua"):
    buttons = PT if language == "pt" else UA

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=buttons["book"])],
            [
                KeyboardButton(text=buttons["services"]),
                KeyboardButton(text=buttons["masters"]),
            ],
            [KeyboardButton(text=buttons["my_bookings"])],
            [KeyboardButton(text=buttons["contacts"])],
        ],
        resize_keyboard=True,
    )


def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=UA["admin_masters"]),
                KeyboardButton(text=UA["admin_services"]),
            ],
            [
                KeyboardButton(text=UA["admin_bookings"]),
                KeyboardButton(text=UA["admin_statistics"]),
            ],
            [
                KeyboardButton(text=UA["admin_clients"]),
                KeyboardButton(text=UA["admin_mailing"]),
            ],
        ],
        resize_keyboard=True,
    )


def back_menu(language: str = "ua"):
    buttons = PT if language == "pt" else UA

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=buttons["main_menu"])],
        ],
        resize_keyboard=True,
    )
