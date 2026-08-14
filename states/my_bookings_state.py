from aiogram.fsm.state import State, StatesGroup


class MyBookingsState(StatesGroup):
    choosing_new_date = State()
    choosing_new_time = State()
    confirming_reschedule = State()
