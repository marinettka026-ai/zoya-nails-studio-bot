from aiogram.fsm.state import State, StatesGroup


class AddMasterState(StatesGroup):
    name = State()
    photo = State()
    description_ua = State()
    description_pt = State()
    telegram_id = State()
    schedule = State()
    calendar_id = State()


class AddServiceState(StatesGroup):
    master = State()
    category = State()
    name_ua = State()
    name_pt = State()
    description_ua = State()
    description_pt = State()
    price = State()
    duration = State()


class MailingState(StatesGroup):
    text = State()
    photo = State()
    confirm = State()


class EditMasterState(StatesGroup):
    choosing_master = State()
    name = State()
    photo = State()
    description_ua = State()
    description_pt = State()
    telegram_id = State()
    schedule = State()
    calendar_id = State()


class EditServiceState(StatesGroup):
    choosing_service = State()
    category = State()
    name_ua = State()
    name_pt = State()
    description_ua = State()
    description_pt = State()
    price = State()
    duration = State()


class ClientNoteState(StatesGroup):
    waiting_note = State()
