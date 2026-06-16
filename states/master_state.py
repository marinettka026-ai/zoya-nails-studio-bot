from aiogram.fsm.state import State, StatesGroup


class MasterBookingState(StatesGroup):
    viewing_booking = State()
    confirming_payment = State()
    rejecting_booking = State()
    contacting_client = State()


class MasterScheduleState(StatesGroup):
    viewing_schedule = State()
    editing_schedule = State()
