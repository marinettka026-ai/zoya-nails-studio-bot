import json
from datetime import datetime, timedelta

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
    total_price: float = 0,
    total_duration: int = 0,
    selected_extras=None,
):
    selected_extras_json = json.dumps(selected_extras or [], ensure_ascii=False)

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            INSERT INTO bookings (
                client_id,
                master_id,
                service_id,
                client_name,
                client_phone,
                date,
                time,
                total_price,
                total_duration,
                selected_extras
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                client_id,
                master_id,
                service_id,
                client_name,
                client_phone,
                date,
                time,
                total_price,
                total_duration,
                selected_extras_json,
            ),
        )
        await db.commit()
        return cursor.lastrowid


def add_minutes(time_str: str, minutes: int) -> str:
    time_obj = datetime.strptime(time_str, "%H:%M")
    return (time_obj + timedelta(minutes=minutes)).strftime("%H:%M")


async def add_booking_service(
    booking_id: int,
    master_id: int,
    service_id: int,
    extras=None,
    position: int = 1,
    price: float = 0,
    duration: int = 0,
    date: str = None,
    start_time: str = None,
    end_time: str = None,
    resource_type: str = None,
):
    extras_json = json.dumps(extras or [], ensure_ascii=False)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO booking_services (
                booking_id,
                master_id,
                service_id,
                extras,
                position,
                price,
                duration,
                date,
                start_time,
                end_time,
                resource_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                booking_id,
                master_id,
                service_id,
                extras_json,
                position,
                price,
                duration,
                date,
                start_time,
                end_time,
                resource_type,
            ),
        )

        await db.commit()


async def get_booking_services(booking_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                booking_services.*,
                services.name_ua,
                services.name_pt,
                services.category_ua,
                services.category_pt,
                masters.name AS master_name
            FROM booking_services
            JOIN services ON booking_services.service_id = services.id
            JOIN masters ON booking_services.master_id = masters.id
            WHERE booking_services.booking_id = ?
            ORDER BY booking_services.position ASC
            """,
            (booking_id,),
        )

        rows = await cursor.fetchall()

        result = []
        for row in rows:
            item = dict(row)

            try:
                item["extras"] = json.loads(item["extras"] or "[]")
            except json.JSONDecodeError:
                item["extras"] = []

            result.append(item)

        return result


async def get_combined_booking_full_info(booking_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                bookings.*,

                users.telegram_id AS client_telegram_id,
                users.language AS client_language,

                masters.name AS master_name,
                masters.telegram_id AS master_telegram_id,
                masters.calendar_id AS master_calendar_id
            FROM bookings
            JOIN users ON bookings.client_id = users.id
            JOIN masters ON bookings.master_id = masters.id
            WHERE bookings.id = ?
            """,
            (booking_id,),
        )

        booking = await cursor.fetchone()

    if not booking:
        return None

    booking_data = dict(booking)
    booking_data["services"] = await get_booking_services(booking_id)

    return booking_data


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
                id,
                date,
                time,
                status,
                total_duration
            FROM bookings
            WHERE master_id = ?
            AND date = ?
            AND status IN (
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


async def get_main_services_by_master(master_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM services
            WHERE master_id = ?
            AND is_active = 1
            AND service_type = 'main'
            ORDER BY category_ua, name_ua
            """,
            (master_id,),
        )

        return await cursor.fetchall()


async def get_service_extras(service_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM service_extras
            WHERE service_id = ?
            AND is_active = 1
            ORDER BY name_ua
            """,
            (service_id,),
        )

        return await cursor.fetchall()


async def get_bookings_by_date(date: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                bookings.*,
                services.resource_type
            FROM bookings
            JOIN services
                ON bookings.service_id = services.id
            WHERE bookings.date = ?
            AND bookings.status IN (
                'waiting_confirmation',
                'confirmed'
            )
            """,
            (date,),
        )

        return await cursor.fetchall()


async def get_resource_usage(date: str):
    bookings = await get_bookings_by_date(date)

    manicure_count = 0
    pedicure_count = 0

    for booking in bookings:
        if booking["resource_type"] == "manicure":
            manicure_count += 1

        elif booking["resource_type"] == "pedicure":
            pedicure_count += 1

    return {
        "manicure": manicure_count,
        "pedicure": pedicure_count,
    }


async def get_extra_by_id(extra_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM service_extras
            WHERE id = ?
            AND is_active = 1
            """,
            (extra_id,),
        )

        return await cursor.fetchone()


async def get_extras_by_ids(extra_ids: list[int]):
    if not extra_ids:
        return []

    placeholders = ",".join("?" for _ in extra_ids)

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            f"""
            SELECT *
            FROM service_extras
            WHERE id IN ({placeholders})
            AND is_active = 1
            """,
            extra_ids,
        )

        return await cursor.fetchall()


async def add_service_extra(
    master_id: int,
    category_ua: str,
    category_pt: str,
    name_ua: str,
    name_pt: str,
    price: float,
    duration: int,
):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO service_extras (
                service_id,
                master_id,
                category_ua,
                category_pt,
                name_ua,
                name_pt,
                price,
                duration,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                0,
                master_id,
                category_ua,
                category_pt,
                name_ua,
                name_pt,
                price,
                duration,
            ),
        )

        await db.commit()


async def get_service_extras_by_category(master_id: int, category_ua: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT *
            FROM service_extras
            WHERE master_id = ?
            AND category_ua = ?
            AND is_active = 1
            ORDER BY name_ua
            """,
            (master_id, category_ua),
        )

        return await cursor.fetchall()


async def get_bookings_with_resource_by_date(date: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT
                bookings.id,
                bookings.master_id,
                bookings.service_id,
                bookings.date,
                bookings.time,
                bookings.status,
                bookings.total_duration,
                services.duration AS service_duration,
                services.resource_type
            FROM bookings
            JOIN services
                ON bookings.service_id = services.id
            WHERE bookings.date = ?
            AND bookings.status IN (
                'waiting_confirmation',
                'confirmed'
            )
            """,
            (date,),
        )

        return await cursor.fetchall()


async def get_resource_capacity(resource_type: str) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT capacity
            FROM salon_resources
            WHERE resource_type = ?
            AND is_active = 1
            """,
            (resource_type,),
        )

        row = await cursor.fetchone()
        return row[0] if row else 1


async def is_master_available(
    master_id: int,
    date: str,
    start_time: str,
    end_time: str,
) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM booking_services bs
            JOIN bookings b ON b.id = bs.booking_id
            WHERE bs.master_id = ?
            AND bs.date = ?
            AND b.status NOT IN ('cancelled', 'rejected')
            AND bs.start_time < ?
            AND bs.end_time > ?
            """,
            (master_id, date, end_time, start_time),
        )

        count = (await cursor.fetchone())[0]
        return count == 0


async def is_resource_available(
    resource_type: str,
    date: str,
    start_time: str,
    end_time: str,
) -> bool:
    capacity = await get_resource_capacity(resource_type)

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM booking_services bs
            JOIN bookings b ON b.id = bs.booking_id
            WHERE bs.resource_type = ?
            AND bs.date = ?
            AND b.status NOT IN ('cancelled', 'rejected')
            AND bs.start_time < ?
            AND bs.end_time > ?
            """,
            (resource_type, date, end_time, start_time),
        )

        busy_count = (await cursor.fetchone())[0]
        return busy_count < capacity


async def build_booking_segments(
    master_id: int,
    service_ids: list[int],
    date: str,
    start_time: str,
):
    segments = []
    current_time = start_time

    for position, service_id in enumerate(service_ids, start=1):
        service = await get_service_by_id(service_id)

        if not service:
            return None

        duration = int(service["duration"])
        end_time = add_minutes(current_time, duration)

        segments.append(
            {
                "master_id": master_id,
                "service_id": service_id,
                "date": date,
                "start_time": current_time,
                "end_time": end_time,
                "resource_type": service["resource_type"],
                "price": float(service["price"]),
                "duration": duration,
                "position": position,
            }
        )

        current_time = end_time

    return segments


async def is_combined_booking_available(
    master_id: int,
    service_ids: list[int],
    date: str,
    start_time: str,
) -> bool:
    segments = await build_booking_segments(
        master_id=master_id,
        service_ids=service_ids,
        date=date,
        start_time=start_time,
    )

    if not segments:
        return False

    for segment in segments:
        master_free = await is_master_available(
            master_id=segment["master_id"],
            date=segment["date"],
            start_time=segment["start_time"],
            end_time=segment["end_time"],
        )

        if not master_free:
            return False

        resource_free = await is_resource_available(
            resource_type=segment["resource_type"],
            date=segment["date"],
            start_time=segment["start_time"],
            end_time=segment["end_time"],
        )

        if not resource_free:
            return False

    return True


async def create_combined_booking(
    client_id: int,
    master_id: int,
    service_ids: list[int],
    client_name: str,
    client_phone: str,
    date: str,
    start_time: str,
    comment: str = None,
):
    segments = await build_booking_segments(
        master_id=master_id,
        service_ids=service_ids,
        date=date,
        start_time=start_time,
    )

    if not segments:
        return None

    available = await is_combined_booking_available(
        master_id=master_id,
        service_ids=service_ids,
        date=date,
        start_time=start_time,
    )

    if not available:
        return None

    total_price = sum(segment["price"] for segment in segments)
    total_duration = sum(segment["duration"] for segment in segments)
    end_time = segments[-1]["end_time"]
    first_service_id = service_ids[0]

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            INSERT INTO bookings (
                client_id,
                master_id,
                service_id,
                client_name,
                client_phone,
                date,
                time,
                end_time,
                total_price,
                total_duration,
                comment,
                status,
                payment_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                client_id,
                master_id,
                first_service_id,
                client_name,
                client_phone,
                date,
                start_time,
                end_time,
                total_price,
                total_duration,
                comment,
                "waiting_confirmation",
                "not_required",
            ),
        )

        booking_id = cursor.lastrowid

        for segment in segments:
            await db.execute(
                """
                INSERT INTO booking_services (
                    booking_id,
                    master_id,
                    service_id,
                    date,
                    start_time,
                    end_time,
                    resource_type,
                    position,
                    price,
                    duration
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    booking_id,
                    segment["master_id"],
                    segment["service_id"],
                    segment["date"],
                    segment["start_time"],
                    segment["end_time"],
                    segment["resource_type"],
                    segment["position"],
                    segment["price"],
                    segment["duration"],
                ),
            )

        await db.commit()
        return booking_id


async def build_booking_segments_from_items(
    selected_services: list[dict],
    date: str,
    start_time: str,
):
    segments = []
    current_time = start_time

    for position, item in enumerate(selected_services, start=1):
        service = await get_service_by_id(item["service_id"])

        if not service:
            return None

        service_duration = int(service["duration"])
        service_price = float(service["price"])

        extras = item.get("extras", [])
        extras_duration = sum(int(extra.get("duration", 0)) for extra in extras)
        extras_price = sum(float(extra.get("price", 0)) for extra in extras)

        duration = service_duration + extras_duration
        price = service_price + extras_price

        end_time = add_minutes(current_time, duration)

        segments.append(
            {
                "master_id": item["master_id"],
                "service_id": item["service_id"],
                "date": date,
                "start_time": current_time,
                "end_time": end_time,
                "resource_type": service["resource_type"],
                "price": price,
                "duration": duration,
                "position": position,
                "extras": extras,
            }
        )

        current_time = end_time

    return segments


async def is_selected_services_available(
    selected_services: list[dict],
    date: str,
    start_time: str,
) -> bool:
    segments = await build_booking_segments_from_items(
        selected_services=selected_services,
        date=date,
        start_time=start_time,
    )

    if not segments:
        return False

    for segment in segments:
        if not await is_master_available(
            master_id=segment["master_id"],
            date=segment["date"],
            start_time=segment["start_time"],
            end_time=segment["end_time"],
        ):
            return False

        if not await is_resource_available(
            resource_type=segment["resource_type"],
            date=segment["date"],
            start_time=segment["start_time"],
            end_time=segment["end_time"],
        ):
            return False

    return True


async def create_booking_from_selected_services(
    client_id: int,
    selected_services: list[dict],
    client_name: str,
    client_phone: str,
    date: str,
    start_time: str,
    comment: str = None,
):
    segments = await build_booking_segments_from_items(
        selected_services=selected_services,
        date=date,
        start_time=start_time,
    )

    if not segments:
        return None

    if not await is_selected_services_available(selected_services, date, start_time):
        return None

    total_price = sum(segment["price"] for segment in segments)
    total_duration = sum(segment["duration"] for segment in segments)
    end_time = segments[-1]["end_time"]

    first_segment = segments[0]

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            INSERT INTO bookings (
                client_id,
                master_id,
                service_id,
                client_name,
                client_phone,
                date,
                time,
                end_time,
                total_price,
                total_duration,
                comment,
                status,
                payment_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                client_id,
                first_segment["master_id"],
                first_segment["service_id"],
                client_name,
                client_phone,
                date,
                start_time,
                end_time,
                total_price,
                total_duration,
                comment,
                "waiting_confirmation",
                "not_required",
            ),
        )

        booking_id = cursor.lastrowid

        for segment in segments:
            await db.execute(
                """
                INSERT INTO booking_services (
                    booking_id,
                    master_id,
                    service_id,
                    date,
                    start_time,
                    end_time,
                    resource_type,
                    extras,
                    position,
                    price,
                    duration
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    booking_id,
                    segment["master_id"],
                    segment["service_id"],
                    segment["date"],
                    segment["start_time"],
                    segment["end_time"],
                    segment["resource_type"],
                    json.dumps(segment["extras"], ensure_ascii=False),
                    segment["position"],
                    segment["price"],
                    segment["duration"],
                ),
            )

        await db.commit()
        return booking_id
