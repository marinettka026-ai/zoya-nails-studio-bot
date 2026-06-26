from aiogram.fsm.state import State, StatesGroup


class AddServiceState(StatesGroup):
    master = State()
    category = State()
    name_ua = State()
    name_pt = State()
    description_ua = State()
    description_pt = State()
    price = State()
    duration = State()


class EditServiceState(StatesGroup):
    service = State()
    category = State()
    name_ua = State()
    name_pt = State()
    description_ua = State()
    description_pt = State()
    price = State()
    duration = State()


class AddMasterState(StatesGroup):
    name = State()
    photo = State()
    description_ua = State()
    description_pt = State()
    telegram_id = State()
    schedule = State()
    calendar_id = State()


class EditMasterState(StatesGroup):
    master = State()
    name = State()
    photo = State()
    description_ua = State()
    description_pt = State()
    telegram_id = State()
    schedule = State()
    calendar_id = State()


class MailingState(StatesGroup):
    text = State()
    photo = State()
    confirm = State()


class ClientNoteState(StatesGroup):
    note = State()
    waiting_note = State()


class AddExtraState(StatesGroup):
    master = State()
    category = State()
    name_ua = State()
    name_pt = State()
    price = State()
    duration = State()
