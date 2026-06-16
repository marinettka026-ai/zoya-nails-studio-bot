import asyncio
import logging

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from database.database import create_tables

from handlers.user.start import router as user_start_router
from handlers.user.booking import router as user_booking_router
from handlers.user.profile import router as user_profile_router

from handlers.admin.admin_panel import router as admin_panel_router
from handlers.admin.masters import router as admin_masters_router
from handlers.admin.statistics import router as admin_statistics_router
from handlers.admin.bookings import router as admin_bookings_router

from handlers.master.bookings import router as master_bookings_router
from handlers.master.schedule import router as master_schedule_router
from handlers.admin.clients import router as admin_clients_router


async def main():
    logging.basicConfig(level=logging.INFO)

    await create_tables()
    print("База даних готова ✅")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(user_start_router)
    dp.include_router(user_booking_router)
    dp.include_router(user_profile_router)

    dp.include_router(admin_panel_router)
    dp.include_router(admin_masters_router)
    dp.include_router(admin_statistics_router)
    dp.include_router(admin_bookings_router)

    dp.include_router(master_bookings_router)
    dp.include_router(master_schedule_router)
    dp.include_router(admin_clients_router)

    print("Бот запущений 🚀")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
