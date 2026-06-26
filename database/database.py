import aiosqlite

DB_NAME = "salon_booking.db"


async def create_tables():
    async with aiosqlite.connect(DB_NAME) as db:

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
            service_id INTEGER NOT NULL,
            client_name TEXT,
            client_phone TEXT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            total_price REAL DEFAULT 0,
            total_duration INTEGER DEFAULT 0,
            selected_extras TEXT,
            status TEXT DEFAULT 'waiting_confirmation',
            payment_status TEXT DEFAULT 'not_required',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES users (id),
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
            FOREIGN KEY (booking_id) REFERENCES bookings (id)
        )
        """)

        # Міграції старої бази
        try:
            await db.execute("ALTER TABLE services ADD COLUMN category_ua TEXT")
        except:
            pass

        try:
            await db.execute("ALTER TABLE services ADD COLUMN category_pt TEXT")
        except:
            pass

        try:
            await db.execute(
                "ALTER TABLE services ADD COLUMN service_type TEXT DEFAULT 'main'"
            )
        except:
            pass

        try:
            await db.execute(
                "ALTER TABLE services ADD COLUMN resource_type TEXT DEFAULT 'manicure'"
            )
        except:
            pass

        try:
            await db.execute("ALTER TABLE masters ADD COLUMN calendar_id TEXT")
        except:
            pass

        try:
            await db.execute(
                "ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0"
            )
        except:
            pass

        try:
            await db.execute("ALTER TABLE users ADD COLUMN note TEXT")
        except:
            pass

        try:
            await db.execute(
                "ALTER TABLE bookings ADD COLUMN total_price REAL DEFAULT 0"
            )
        except:
            pass

        try:
            await db.execute(
                "ALTER TABLE bookings ADD COLUMN total_duration INTEGER DEFAULT 0"
            )
        except:
            pass

        try:
            await db.execute("ALTER TABLE bookings ADD COLUMN selected_extras TEXT")
        except:
            pass

        try:
            await db.execute(
                "ALTER TABLE bookings ADD COLUMN payment_status TEXT DEFAULT 'not_required'"
            )
        except:
            pass

        try:
            await db.execute("ALTER TABLE service_extras ADD COLUMN master_id INTEGER")
        except:
            pass

        try:
            await db.execute("ALTER TABLE service_extras ADD COLUMN category_ua TEXT")
        except:
            pass

        try:
            await db.execute("ALTER TABLE service_extras ADD COLUMN category_pt TEXT")
        except:
            pass

        await db.commit()
