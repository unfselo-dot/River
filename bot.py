import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from config import BOT_TOKEN, ADMINS, MAX_PLAYERS
from db import (
    init_db, upsert_player, create_game, set_game_message, get_open_game,
    count_main_players, get_registration, register_player, cancel_registration,
    get_waitlist_first, promote_waitlist, mark_paid, get_game_lists, close_game
)
from keyboards import game_keyboard

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def render_players(rows):
    main = []
    wait = []
    for idx, row in enumerate(rows, start=1):
        name = row[1] or f"user_{row[0]}"
        paid_mark = "💸" if row[4] else "—"
        line = f"{name} ({paid_mark})"
        if row[3] == "main":
            main.append(line)
        else:
            wait.append(line)

    text = "🏟 <b>Состав на игру</b>\n\n"
    text += "<b>Основа:</b>\n"
    if main:
        for i, x in enumerate(main, start=1):
            text += f"{i}. {x}\n"
    else:
        text += "пока пусто\n"

    text += "\n<b>Запас:</b>\n"
    if wait:
        for i, x in enumerate(wait, start=1):
            text += f"{i}. {x}\n"
    else:
        text += "пока пусто\n"

    return text

async def update_game_post(game_id: int):
    game = await get_open_game()
    if not game or game["id"] != game_id:
        return

    rows = await get_game_lists(game_id)
    text = (
        f"⚽ <b>{game['title']}</b>\n"
        f"📅 {game['game_date']} {game['game_time']}\n"
        f"📍 {game['location']}\n"
        f"💰 {game['price']} грн\n\n"
        f"{render_players(rows)}\n"
        f"\nЛимит: {MAX_PLAYERS} игроков"
    )

    await bot.edit_message_text(
        chat_id=game["chat_id"],
        message_id=game["message_id"],
        text=text,
        reply_markup=game_keyboard(game_id),
        parse_mode="HTML"
    )

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await upsert_player(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username
    )
    await message.answer("River Team Bot активирован ✅")

@dp.message(Command("newgame"))
async def cmd_newgame(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("Только админ может создавать игру.")

    # Формат:
    # /newgame Пн|2026-03-30|21:00|Поле River|150
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        return await message.answer(
            "Формат:\n/newgame Понедельник|2026-03-30|21:00|Поле River|150"
        )

    try:
        title, game_date, game_time, location, price = parts[1].split("|")
        game_id = await create_game(title, game_date, game_time, location, int(price), message.chat.id)

        sent = await message.answer(
            f"⚽ <b>{title}</b>\n"
            f"📅 {game_date} {game_time}\n"
            f"📍 {location}\n"
            f"💰 {price} грн\n\n"
            f"🏟 <b>Состав на игру</b>\n\n"
            f"<b>Основа:</b>\nпока пусто\n\n"
            f"<b>Запас:</b>\nпока пусто\n\n"
            f"Лимит: {MAX_PLAYERS} игроков",
            reply_markup=game_keyboard(game_id),
            parse_mode="HTML"
        )
        await set_game_message(game_id, sent.message_id)
    except Exception:
        await message.answer("Ошибка формата. Проверь команду.")

@dp.callback_query(F.data.startswith("join:"))
async def join_game(callback: CallbackQuery):
    game_id = int(callback.data.split(":")[1])
    await upsert_player(
        user_id=callback.from_user.id,
        full_name=callback.from_user.full_name,
        username=callback.from_user.username
    )

    reg = await get_registration(game_id, callback.from_user.id)
    if reg and reg["status"] in ("main", "waitlist"):
        return await callback.answer("Ты уже записан.", show_alert=True)

    main_count = await count_main_players(game_id)
    status = "main" if main_count < MAX_PLAYERS else "waitlist"
    await register_player(game_id, callback.from_user.id, status)
    await update_game_post(game_id)
    await callback.answer("Ты записан." if status == "main" else "Ты в запасе.")

@dp.callback_query(F.data.startswith("leave:"))
async def leave_game(callback: CallbackQuery):
    game_id = int(callback.data.split(":")[1])
    reg = await get_registration(game_id, callback.from_user.id)

    if not reg or reg["status"] == "canceled":
        return await callback.answer("Ты не записан.", show_alert=True)

    was_main = reg["status"] == "main"
    await cancel_registration(game_id, callback.from_user.id)

    if was_main:
        wait = await get_waitlist_first(game_id)
        if wait:
            await promote_waitlist(game_id, wait["user_id"])
            try:
                await bot.send_message(wait["user_id"], "Ты переведен из запаса в основной состав ⚽")
            except Exception:
                pass

    await update_game_post(game_id)
    await callback.answer("Участие отменено.")

@dp.callback_query(F.data.startswith("paid:"))
async def paid_game(callback: CallbackQuery):
    game_id = int(callback.data.split(":")[1])
    reg = await get_registration(game_id, callback.from_user.id)

    if not reg or reg["status"] not in ("main", "waitlist"):
        return await callback.answer("Сначала запишись на игру.", show_alert=True)

    await mark_paid(game_id, callback.from_user.id)
    await update_game_post(game_id)
    await callback.answer("Оплата отмечена.")

@dp.message(Command("players"))
async def cmd_players(message: Message):
    game = await get_open_game()
    if not game:
        return await message.answer("Сейчас нет открытой игры.")
    rows = await get_game_lists(game["id"])
    await message.answer(render_players(rows), parse_mode="HTML")

@dp.message(Command("closegame"))
async def cmd_closegame(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("Только админ может закрыть игру.")
    game = await get_open_game()
    if not game:
        return await message.answer("Нет открытой игры.")
    await close_game(game["id"])
    await message.answer("Регистрация закрыта ✅")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())