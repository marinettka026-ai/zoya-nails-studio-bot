from aiogram.fsm.state import State, StatesGroup


class BookingState(StatesGroup):
    rules = State()

    choosing_master = State()
    choosing_category = State()
    choosing_service = State()
    choosing_extras = State()

    choosing_date = State()
    choosing_time = State()

    entering_name = State()
    entering_phone = State()

    confirming_booking = State()

    waiting_master_confirmation = State()
