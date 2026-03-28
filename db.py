import aiosqlite
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            birthday TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            game_date TEXT,
            game_time TEXT,
            location TEXT,
            price INTEGER,
            status TEXT DEFAULT 'open',
            message_id INTEGER,
            chat_id INTEGER
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            user_id INTEGER,
            status TEXT,         -- main / waitlist / canceled
            paid INTEGER DEFAULT 0,
            UNIQUE(game_id, user_id)
        )
        """)
        await db.commit()

async def upsert_player(user_id: int, full_name: str, username: str | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO players (user_id, full_name, username)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            full_name=excluded.full_name,
            username=excluded.username
        """, (user_id, full_name, username))
        await db.commit()

async def create_game(title: str, game_date: str, game_time: str, location: str, price: int, chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
        INSERT INTO games (title, game_date, game_time, location, price, chat_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (title, game_date, game_time, location, price, chat_id))
        await db.commit()
        return cur.lastrowid

async def set_game_message(game_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE games SET message_id=? WHERE id=?", (message_id, game_id))
        await db.commit()

async def get_open_game():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
        SELECT * FROM games
        WHERE status='open'
        ORDER BY id DESC
        LIMIT 1
        """)
        return await cur.fetchone()

async def count_main_players(game_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
        SELECT COUNT(*) FROM registrations
        WHERE game_id=? AND status='main'
        """, (game_id,))
        row = await cur.fetchone()
        return row[0]

async def get_registration(game_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
        SELECT * FROM registrations
        WHERE game_id=? AND user_id=?
        """, (game_id, user_id))
        return await cur.fetchone()

async def register_player(game_id: int, user_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT OR REPLACE INTO registrations (game_id, user_id, status, paid)
        VALUES (
            ?, ?,
            ?,
            COALESCE((SELECT paid FROM registrations WHERE game_id=? AND user_id=?), 0)
        )
        """, (game_id, user_id, status, game_id, user_id))
        await db.commit()

async def cancel_registration(game_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE registrations
        SET status='canceled'
        WHERE game_id=? AND user_id=?
        """, (game_id, user_id))
        await db.commit()

async def get_waitlist_first(game_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
        SELECT * FROM registrations
        WHERE game_id=? AND status='waitlist'
        ORDER BY id ASC
        LIMIT 1
        """, (game_id,))
        return await cur.fetchone()

async def promote_waitlist(game_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE registrations
        SET status='main'
        WHERE game_id=? AND user_id=?
        """, (game_id, user_id))
        await db.commit()

async def mark_paid(game_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE registrations
        SET paid=1
        WHERE game_id=? AND user_id=?
        """, (game_id, user_id))
        await db.commit()

async def get_game_lists(game_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
        SELECT r.user_id, p.full_name, p.username, r.status, r.paid
        FROM registrations r
        LEFT JOIN players p ON p.user_id = r.user_id
        WHERE r.game_id=? AND r.status IN ('main', 'waitlist')
        ORDER BY
            CASE WHEN r.status='main' THEN 0 ELSE 1 END,
            r.id ASC
        """, (game_id,))
        return await cur.fetchall()

async def close_game(game_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE games SET status='closed' WHERE id=?", (game_id,))
        await db.commit()