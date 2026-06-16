from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from locales.ua import BUTTONS as UA
from locales.pt import BUTTONS as PT


def get_buttons(language: str = "ua"):
    return PT if language == "pt" else UA


def booking_rules_keyboard(language: str = "ua"):
    buttons = get_buttons(language)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=buttons["rules_accept"],
                    callback_data="rules_accept",
                )
            ],
            [
                InlineKeyboardButton(
                    text=buttons["back"],
                    callback_data="back_main",
                )
            ],
        ]
    )


def booking_confirm_keyboard(language: str = "ua"):
    buttons = get_buttons(language)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=buttons["confirm"],
                    callback_data="confirm_booking",
                )
            ],
            [
                InlineKeyboardButton(
                    text=buttons["change"],
                    callback_data="change_booking",
                )
            ],
            [
                InlineKeyboardButton(
                    text=buttons["back"],
                    callback_data="back_to_dates",
                )
            ],
        ]
    )


def deposit_keyboard(language: str = "ua"):
    buttons = get_buttons(language)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=buttons["paid"],
                    callback_data="deposit_paid",
                )
            ],
            [
                InlineKeyboardButton(
                    text=buttons["back"],
                    callback_data="back_to_confirm",
                )
            ],
        ]
    )


def master_booking_keyboard(language: str = "ua"):
    buttons = get_buttons(language)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=buttons["master_confirm_payment"],
                    callback_data="master_confirm_payment",
                )
            ],
            [
                InlineKeyboardButton(
                    text=buttons["master_reject"],
                    callback_data="master_reject",
                )
            ],
            [
                InlineKeyboardButton(
                    text=buttons["master_contact_client"],
                    callback_data="master_contact_client",
                )
            ],
        ]
    )
