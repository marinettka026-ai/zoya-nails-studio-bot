from aiogram.fsm.state import State, StatesGroup


class BookingState(StatesGroup):
    # Застарілі стани поки залишаємо для сумісності
    rules = State()
    choosing_category = State()
    choosing_service = State()
    choosing_extras = State()
    entering_name = State()
    entering_phone = State()

    # Новий сценарій запису
    choosing_master = State()
    choosing_gender = State()
    choosing_services = State()
    choosing_additional_service = State()

    choosing_date = State()
    choosing_time = State()

    sharing_phone = State()
    confirming_booking = State()

    waiting_master_confirmation = State()
