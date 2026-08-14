from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)


def phone_keyboard(language: str = "ua") -> ReplyKeyboardMarkup:
    if language == "pt":
        button_text = "📱 Partilhar número de telefone"
    else:
        button_text = "📱 Поділитися номером телефону"

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=button_text,
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder=button_text,
    )


def remove_reply_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
