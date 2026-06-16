import aiosqlite
from database.database import DB_NAME


async def add_user(
    telegram_id: int,
    name: str = None,
    phone: str = None,
    language: str = "ua",
    role: str = "client",
):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
        INSERT OR IGNORE INTO users (telegram_id, name, phone, language, role)
        VALUES (?, ?, ?, ?, ?)
        """,
            (telegram_id, name, phone, language, role),
        )
        await db.commit()


async def delete_master(master_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            DELETE FROM services
            WHERE master_id = ?
            """,
            (master_id,),
        )

        await db.execute(
            """
            DELETE FROM masters
            WHERE id = ?
            """,
            (master_id,),
        )

        await db.commit()


async def get_user_by_telegram_id(telegram_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
        SELECT * FROM users WHERE telegram_id = ?
        """,
            (telegram_id,),
        )
        return await cursor.fetchone()


async def update_user_language(telegram_id: int, language: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
        UPDATE users SET language = ? WHERE telegram_id = ?
        """,
            (language, telegram_id),
        )
        await db.commit()


async def accept_rules(telegram_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
        UPDATE users SET rules_accepted = 1 WHERE telegram_id = ?
        """,
            (telegram_id,),
        )
        await db.commit()


async def add_master(
    name: str,
    telegram_id: int = None,
    photo_id: str = None,
    description_ua: str = None,
    description_pt: str = None,
    schedule: str = None,
    calendar_id: str = None,
):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
        INSERT INTO masters (
            name, telegram_id, photo_id, description_ua, description_pt, schedule, calendar_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                name,
                telegram_id,
                photo_id,
                description_ua,
                description_pt,
                schedule,
                calendar_id,
            ),
        )
        await db.commit()


async def get_active_masters():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
        SELECT * FROM masters WHERE is_active = 1
        """)
        return await cursor.fetchall()


async def get_master_by_id(master_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
        SELECT * FROM masters WHERE id = ?
        """,
            (master_id,),
        )
        return await cursor.fetchone()


async def add_service(
    master_id: int,
    name_ua: str,
    price: float,
    duration: int,
    deposit_amount: float = 0,
    name_pt: str = None,
    description_ua: str = None,
    description_pt: str = None,
    category_ua: str = None,
    category_pt: str = None,
):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO services (
                master_id,
                category_ua,
                category_pt,
                name_ua,
                name_pt,
                description_ua,
                description_pt,
                price,
                duration,
                deposit_amount
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                master_id,
                category_ua,
                category_pt,
                name_ua,
                name_pt,
                description_ua,
                description_pt,
                price,
                duration,
                deposit_amount,
            ),
        )
        await db.commit()


async def get_services_by_master(master_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
        SELECT * FROM services
        WHERE master_id = ? AND is_active = 1
        """,
            (master_id,),
        )
        return await cursor.fetchall()


async def get_service_by_id(service_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
        SELECT * FROM services WHERE id = ?
        """,
            (service_id,),
        )
        return await cursor.fetchone()


async def create_booking(
    client_id: int,
    master_id: int,
    service_id: int,
    client_name: str,
    client_phone: str,
    date: str,
    time: str,
):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
        INSERT INTO bookings (
            client_id, master_id, service_id, client_name, client_phone, date, time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (client_id, master_id, service_id, client_name, client_phone, date, time),
        )
        await db.commit()
        return cursor.lastrowid


async def get_booking_by_id(booking_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
        SELECT * FROM bookings WHERE id = ?
        """,
            (booking_id,),
        )
        return await cursor.fetchone()


async def update_booking_status(booking_id: int, status: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
        UPDATE bookings SET status = ? WHERE id = ?
        """,
            (status, booking_id),
        )
        await db.commit()


async def update_payment_status(booking_id: int, payment_status: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
        UPDATE bookings SET payment_status = ? WHERE id = ?
        """,
            (payment_status, booking_id),
        )
        await db.commit()


async def get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
        SELECT * FROM users
        """)
        return await cursor.fetchall()


async def get_all_bookings():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
        SELECT
            bookings.id,
            bookings.client_name,
            bookings.client_phone AS phone,
            bookings.date,
            bookings.time,
            bookings.status,
            bookings.payment_status,
            masters.name AS master_name,
            services.name_ua AS service_name,
            bookings.date || ' ' || bookings.time AS datetime
        FROM bookings
        LEFT JOIN masters ON bookings.master_id = masters.id
        LEFT JOIN services ON bookings.service_id = services.id
        ORDER BY bookings.date DESC, bookings.time DESC
        """)

        return await cursor.fetchall()


async def get_future_bookings():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
        SELECT
            bookings.id,
            bookings.client_name,
            bookings.client_phone AS phone,
            bookings.date,
            bookings.time,
            bookings.status,
            bookings.payment_status,
            masters.name AS master_name,
            services.name_ua AS service_name,
            bookings.date || ' ' || bookings.time AS datetime
        FROM bookings
        LEFT JOIN masters ON bookings.master_id = masters.id
        LEFT JOIN services ON bookings.service_id = services.id
        WHERE datetime(bookings.date || ' ' || bookings.time) >= datetime('now', 'localtime')
        ORDER BY bookings.date ASC, bookings.time ASC
        """)

        return await cursor.fetchall()


async def get_past_bookings():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
        SELECT
            bookings.id,
            bookings.client_name,
            bookings.client_phone AS phone,
            bookings.date,
            bookings.time,
            bookings.status,
            bookings.payment_status,
            masters.name AS master_name,
            services.name_ua AS service_name,
            bookings.date || ' ' || bookings.time AS datetime
        FROM bookings
        LEFT JOIN masters ON bookings.master_id = masters.id
        LEFT JOIN services ON bookings.service_id = services.id
        WHERE datetime(bookings.date || ' ' || bookings.time) < datetime('now', 'localtime')
        ORDER BY bookings.date DESC, bookings.time DESC
        """)

        return await cursor.fetchall()


async def get_booking_full_info(booking_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                bookings.id AS booking_id,
                bookings.client_name,
                bookings.client_phone,
                bookings.date,
                bookings.time,
                bookings.status,
                bookings.payment_status,

                users.telegram_id AS client_telegram_id,
                users.language AS client_language,

                masters.id AS master_id,
                masters.name AS master_name,
                masters.telegram_id AS master_telegram_id,
                masters.calendar_id AS calendar_id,

                services.id AS service_id,
                services.name_ua,
                services.name_pt,
                services.price,
                services.duration,
                services.deposit_amount
            FROM bookings
            JOIN users ON bookings.client_id = users.id
            JOIN masters ON bookings.master_id = masters.id
            JOIN services ON bookings.service_id = services.id
            WHERE bookings.id = ?
            """,
            (booking_id,),
        )

        return await cursor.fetchone()


async def get_service_categories_by_master(master_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
        SELECT DISTINCT category_ua, category_pt
        FROM services
        WHERE master_id = ? AND is_active = 1
        """,
            (master_id,),
        )

        return await cursor.fetchall()


async def get_services_by_master_and_category(master_id: int, category_ua: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
        SELECT *
        FROM services
        WHERE master_id = ?
        AND category_ua = ?
        AND is_active = 1
        """,
            (master_id, category_ua),
        )

        return await cursor.fetchall()


async def get_all_services():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
        SELECT *
        FROM services
        WHERE is_active = 1
        ORDER BY category_ua, price
        """)

        return await cursor.fetchall()


async def update_master(
    master_id: int,
    name: str = None,
    telegram_id: int = None,
    photo_id: str = None,
    description_ua: str = None,
    description_pt: str = None,
    schedule: str = None,
    calendar_id: str = None,
):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            UPDATE masters
            SET name = ?,
                telegram_id = ?,
                photo_id = ?,
                description_ua = ?,
                description_pt = ?,
                schedule = ?,
                calendar_id = ?
            WHERE id = ?
            """,
            (
                name,
                telegram_id,
                photo_id,
                description_ua,
                description_pt,
                schedule,
                calendar_id,
                master_id,
            ),
        )
        await db.commit()


async def deactivate_master(master_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            UPDATE masters
            SET is_active = 0
            WHERE id = ?
            """,
            (master_id,),
        )
        await db.commit()


async def get_all_masters():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
        SELECT *
        FROM masters
        ORDER BY is_active DESC, name
        """)

        return await cursor.fetchall()


async def get_all_services_admin():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
        SELECT 
            services.*,
            masters.name AS master_name
        FROM services
        JOIN masters ON services.master_id = masters.id
        WHERE services.is_active = 1
        ORDER BY masters.name, services.category_ua, services.name_ua
        """)

        return await cursor.fetchall()


async def update_service(
    service_id: int,
    category_ua: str,
    category_pt: str,
    name_ua: str,
    name_pt: str,
    description_ua: str,
    description_pt: str,
    price: float,
    duration: int,
    deposit_amount: float,
):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
        UPDATE services
        SET category_ua = ?,
            category_pt = ?,
            name_ua = ?,
            name_pt = ?,
            description_ua = ?,
            description_pt = ?,
            price = ?,
            duration = ?,
            deposit_amount = ?
        WHERE id = ?
        """,
            (
                category_ua,
                category_pt,
                name_ua,
                name_pt,
                description_ua,
                description_pt,
                price,
                duration,
                deposit_amount,
                service_id,
            ),
        )

        await db.commit()


async def deactivate_service(service_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
        UPDATE services
        SET is_active = 0
        WHERE id = ?
        """,
            (service_id,),
        )

        await db.commit()


async def delete_all_bookings():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM bookings")
        await db.commit()


async def get_busy_bookings_by_master_and_date(master_id: int, date: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                bookings.id,
                bookings.date,
                bookings.time,
                bookings.status,
                services.duration
            FROM bookings
            JOIN services ON bookings.service_id = services.id
            WHERE bookings.master_id = ?
            AND bookings.date = ?
            AND bookings.status IN (
                'pending_payment',
                'waiting_confirmation',
                'confirmed'
            )
            """,
            (master_id, date),
        )

        return await cursor.fetchall()


async def get_clients_with_stats():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
        SELECT
            users.id,
            users.telegram_id,
            users.name,
            users.phone,
            users.language,
            users.is_blocked,
            users.note,
            users.created_at,
            COUNT(bookings.id) AS bookings_count
        FROM users
        LEFT JOIN bookings ON users.id = bookings.client_id
        WHERE users.role = 'client'
        GROUP BY users.id
        ORDER BY users.created_at DESC
        """)

        return await cursor.fetchall()


async def get_client_by_id(client_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                users.*,
                COUNT(bookings.id) AS bookings_count
            FROM users
            LEFT JOIN bookings ON users.id = bookings.client_id
            WHERE users.id = ?
            GROUP BY users.id
            """,
            (client_id,),
        )

        return await cursor.fetchone()


async def update_client_note(client_id: int, note: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            UPDATE users
            SET note = ?
            WHERE id = ?
            """,
            (note, client_id),
        )
        await db.commit()


async def set_client_blocked(client_id: int, is_blocked: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            UPDATE users
            SET is_blocked = ?
            WHERE id = ?
            """,
            (is_blocked, client_id),
        )
        await db.commit()
