import asyncio
import logging
from contextlib import suppress
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from database.database import create_tables
from database.queries import get_bookings_for_reminder

from handlers.user.start import router as user_start_router
from handlers.user.booking import router as user_booking_router
from handlers.user.profile import router as user_profile_router
from handlers.user.my_bookings import router as user_my_bookings_router

from handlers.admin.admin_panel import router as admin_panel_router
from handlers.admin.masters import router as admin_masters_router
from handlers.admin.statistics import router as admin_statistics_router
from handlers.admin.bookings import router as admin_bookings_router
from handlers.admin.clients import router as admin_clients_router

from handlers.master.bookings import router as master_bookings_router
from handlers.master.schedule import router as master_schedule_router

from services.notifications import send_client_booking_reminder

LISBON_TZ = ZoneInfo("Europe/Lisbon")
REMINDER_CHECK_INTERVAL = 300  # 5 хвилин


async def reminder_worker(bot: Bot):
    while True:
        try:
            now = datetime.now(LISBON_TZ)
            window_end = now + timedelta(hours=24)

            bookings = await get_bookings_for_reminder(
                window_start=now.strftime("%Y-%m-%d %H:%M:%S"),
                window_end=window_end.strftime("%Y-%m-%d %H:%M:%S"),
            )

            for booking in bookings:
                booking_id = booking["booking_id"]

                try:
                    sent = await send_client_booking_reminder(
                        bot=bot,
                        booking_id=booking_id,
                    )

                    if sent:
                        logging.info(
                            "Нагадування надіслано для booking_id=%s",
                            booking_id,
                        )
                except Exception:
                    logging.exception(
                        "Помилка надсилання нагадування для booking_id=%s",
                        booking_id,
                    )

        except Exception:
            logging.exception("Помилка під час перевірки нагадувань")

        await asyncio.sleep(REMINDER_CHECK_INTERVAL)


async def main():
    logging.basicConfig(level=logging.INFO)

    await create_tables()
    print("База даних готова ✅")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(user_start_router)
    dp.include_router(user_booking_router)
    dp.include_router(user_profile_router)
    dp.include_router(user_my_bookings_router)

    dp.include_router(admin_panel_router)
    dp.include_router(admin_masters_router)
    dp.include_router(admin_statistics_router)
    dp.include_router(admin_bookings_router)
    dp.include_router(admin_clients_router)

    dp.include_router(master_bookings_router)
    dp.include_router(master_schedule_router)

    reminder_task = asyncio.create_task(reminder_worker(bot))

    print("Бот запущений 🚀")

    try:
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()

        with suppress(asyncio.CancelledError):
            await reminder_task

        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
