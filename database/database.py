import os
import aiosqlite

DB_NAME = os.getenv("DB_NAME", "salon_booking.db")


async def add_column(db, table, column_sql):
    try:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column_sql}")
    except Exception:
        pass


async def create_tables():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA foreign_keys = ON")

        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            name TEXT,
            phone TEXT,
            language TEXT DEFAULT 'ua',
            role TEXT DEFAULT 'client',
            rules_accepted INTEGER DEFAULT 0,
            is_blocked INTEGER DEFAULT 0,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS masters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            telegram_id INTEGER UNIQUE,
            name TEXT NOT NULL,
            photo_id TEXT,
            description_ua TEXT,
            description_pt TEXT,
            is_active INTEGER DEFAULT 1,
            schedule TEXT,
            calendar_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS salon_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_type TEXT UNIQUE NOT NULL,
            name_ua TEXT NOT NULL,
            name_pt TEXT,
            capacity INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER DEFAULT 1
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id INTEGER NOT NULL,
            category_ua TEXT,
            category_pt TEXT,
            name_ua TEXT NOT NULL,
            name_pt TEXT,
            description_ua TEXT,
            description_pt TEXT,
            price REAL NOT NULL,
            duration INTEGER NOT NULL,
            service_type TEXT DEFAULT 'main',
            deposit_amount REAL DEFAULT 0,
            resource_type TEXT DEFAULT 'manicure',
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (master_id) REFERENCES masters (id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS service_extras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id INTEGER,
            master_id INTEGER,
            category_ua TEXT,
            category_pt TEXT,
            name_ua TEXT NOT NULL,
            name_pt TEXT,
            price REAL DEFAULT 0,
            duration INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (service_id) REFERENCES services (id),
            FOREIGN KEY (master_id) REFERENCES masters (id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            master_id INTEGER NOT NULL,
            service_id INTEGER,
            client_name TEXT,
            client_phone TEXT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            end_time TEXT,
            total_price REAL DEFAULT 0,
            total_duration INTEGER DEFAULT 0,
            selected_extras TEXT,
            comment TEXT,
            status TEXT DEFAULT 'waiting_confirmation',
            payment_status TEXT DEFAULT 'not_required',
            calendar_event_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES users (id),
            FOREIGN KEY (master_id) REFERENCES masters (id),
            FOREIGN KEY (service_id) REFERENCES services (id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS booking_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            master_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            resource_type TEXT,
            extras TEXT,
            position INTEGER DEFAULT 1,
            price REAL DEFAULT 0,
            duration INTEGER DEFAULT 0,
            FOREIGN KEY (booking_id)
                REFERENCES bookings (id)
                ON DELETE CASCADE,
            FOREIGN KEY (master_id) REFERENCES masters (id),
            FOREIGN KEY (service_id) REFERENCES services (id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            method TEXT DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (booking_id)
                REFERENCES bookings (id)
                ON DELETE CASCADE
        )
        """)

        # ===== Міграції старої бази =====

        await add_column(db, "services", "category_ua TEXT")
        await add_column(db, "services", "category_pt TEXT")
        await add_column(
            db,
            "services",
            "service_type TEXT DEFAULT 'main'",
        )
        await add_column(
            db,
            "services",
            "deposit_amount REAL DEFAULT 0",
        )
        await add_column(
            db,
            "services",
            "resource_type TEXT DEFAULT 'manicure'",
        )

        await add_column(db, "masters", "calendar_id TEXT")

        await add_column(
            db,
            "users",
            "is_blocked INTEGER DEFAULT 0",
        )
        await add_column(db, "users", "note TEXT")

        await add_column(db, "bookings", "end_time TEXT")
        await add_column(
            db,
            "bookings",
            "total_price REAL DEFAULT 0",
        )
        await add_column(
            db,
            "bookings",
            "total_duration INTEGER DEFAULT 0",
        )
        await add_column(
            db,
            "bookings",
            "selected_extras TEXT",
        )
        await add_column(db, "bookings", "comment TEXT")
        await add_column(
            db,
            "bookings",
            "payment_status TEXT DEFAULT 'not_required'",
        )
        await add_column(
            db,
            "bookings",
            "calendar_event_id TEXT",
        )

        await add_column(db, "booking_services", "date TEXT")
        await add_column(db, "booking_services", "start_time TEXT")
        await add_column(db, "booking_services", "end_time TEXT")
        await add_column(
            db,
            "booking_services",
            "resource_type TEXT",
        )
        await add_column(db, "booking_services", "extras TEXT")
        await add_column(
            db,
            "booking_services",
            "position INTEGER DEFAULT 1",
        )
        await add_column(
            db,
            "booking_services",
            "price REAL DEFAULT 0",
        )
        await add_column(
            db,
            "booking_services",
            "duration INTEGER DEFAULT 0",
        )

        await add_column(
            db,
            "service_extras",
            "master_id INTEGER",
        )
        await add_column(
            db,
            "service_extras",
            "category_ua TEXT",
        )
        await add_column(
            db,
            "service_extras",
            "category_pt TEXT",
        )

        # ===== Ресурси студії =====
        # Манікюрних місць — 2.
        # Педикюрне місце — 1.

        await db.execute("""
        INSERT INTO salon_resources (
            resource_type,
            name_ua,
            name_pt,
            capacity,
            is_active
        )
        VALUES (
            'manicure',
            'Манікюрне місце',
            'Lugar de manicure',
            2,
            1
        )
        ON CONFLICT(resource_type) DO UPDATE SET
            name_ua = excluded.name_ua,
            name_pt = excluded.name_pt,
            capacity = 2,
            is_active = 1
        """)

        await db.execute("""
        INSERT INTO salon_resources (
            resource_type,
            name_ua,
            name_pt,
            capacity,
            is_active
        )
        VALUES (
            'pedicure',
            'Педикюрне крісло',
            'Lugar de pedicure',
            1,
            1
        )
        ON CONFLICT(resource_type) DO UPDATE SET
            name_ua = excluded.name_ua,
            name_pt = excluded.name_pt,
            capacity = 1,
            is_active = 1
        """)

        # ===== Виправлення resource_type у старих послугах =====

        # Спочатку всі манікюрні послуги
        await db.execute("""
        UPDATE services
        SET resource_type = 'manicure'
        WHERE
            LOWER(COALESCE(name_ua, '')) LIKE '%манікюр%'
            OR LOWER(COALESCE(name_ua, '')) LIKE '%маникюр%'
            OR LOWER(COALESCE(name_ua, '')) LIKE '%манекюр%'
            OR LOWER(COALESCE(category_ua, '')) LIKE '%манікюр%'
            OR LOWER(COALESCE(category_ua, '')) LIKE '%маникюр%'
            OR LOWER(COALESCE(category_ua, '')) LIKE '%манекюр%'
            OR LOWER(COALESCE(name_pt, '')) LIKE '%manicure%'
            OR LOWER(COALESCE(category_pt, '')) LIKE '%manicure%'
        """)

        # Потім педикюрні послуги
        await db.execute("""
        UPDATE services
        SET resource_type = 'pedicure'
        WHERE
            LOWER(COALESCE(name_ua, '')) LIKE '%педикюр%'
            OR LOWER(COALESCE(category_ua, '')) LIKE '%педикюр%'
            OR LOWER(COALESCE(name_pt, '')) LIKE '%pedicure%'
            OR LOWER(COALESCE(category_pt, '')) LIKE '%pedicure%'
        """)

        # Синхронізація старих booking_services
        # із правильним ресурсом самої послуги.
        await db.execute("""
        UPDATE booking_services
        SET resource_type = (
            SELECT services.resource_type
            FROM services
            WHERE services.id = booking_services.service_id
        )
        WHERE EXISTS (
            SELECT 1
            FROM services
            WHERE services.id = booking_services.service_id
        )
        """)

        # ===== Індекси для швидкої перевірки часу =====

        await db.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_booking_services_resource_time
        ON booking_services (
            date,
            resource_type,
            start_time,
            end_time
        )
        """)

        await db.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_booking_services_master_time
        ON booking_services (
            master_id,
            date,
            start_time,
            end_time
        )
        """)

        await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_bookings_status
        ON bookings (status)
        """)

        await db.commit()

        # Міграції
        await add_column(db, "services", "category_ua TEXT")
        await add_column(db, "services", "category_pt TEXT")
        await add_column(db, "services", "service_type TEXT DEFAULT 'main'")
        await add_column(db, "services", "deposit_amount REAL DEFAULT 0")
        await add_column(db, "services", "resource_type TEXT DEFAULT 'manicure'")

        await add_column(db, "masters", "calendar_id TEXT")

        await add_column(db, "users", "is_blocked INTEGER DEFAULT 0")
        await add_column(db, "users", "note TEXT")

        await add_column(db, "bookings", "end_time TEXT")
        await add_column(db, "bookings", "total_price REAL DEFAULT 0")
        await add_column(db, "bookings", "total_duration INTEGER DEFAULT 0")
        await add_column(db, "bookings", "selected_extras TEXT")
        await add_column(db, "bookings", "comment TEXT")
        await add_column(db, "bookings", "payment_status TEXT DEFAULT 'not_required'")
        await add_column(db, "bookings", "calendar_event_id TEXT")

        await add_column(db, "booking_services", "date TEXT")
        await add_column(db, "booking_services", "start_time TEXT")
        await add_column(db, "booking_services", "end_time TEXT")
        await add_column(db, "booking_services", "resource_type TEXT")
        await add_column(db, "booking_services", "extras TEXT")
        await add_column(db, "booking_services", "position INTEGER DEFAULT 1")
        await add_column(db, "booking_services", "price REAL DEFAULT 0")
        await add_column(db, "booking_services", "duration INTEGER DEFAULT 0")

        await add_column(db, "service_extras", "master_id INTEGER")
        await add_column(db, "service_extras", "category_ua TEXT")
        await add_column(db, "service_extras", "category_pt TEXT")

        # Індекси для швидкої перевірки зайнятості
        await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_booking_services_resource_time
        ON booking_services (date, resource_type, start_time, end_time)
        """)

        await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_booking_services_master_time
        ON booking_services (master_id, date, start_time, end_time)
        """)

        await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_bookings_status
        ON bookings (status)
        """)

        await db.commit()
