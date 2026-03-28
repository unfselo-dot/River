from aiogram.utils.keyboard import InlineKeyboardBuilder

def game_keyboard(game_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Записаться", callback_data=f"join:{game_id}")
    kb.button(text="❌ Отменить", callback_data=f"leave:{game_id}")
    kb.button(text="💸 Я оплатил", callback_data=f"paid:{game_id}")
    kb.adjust(1)
    return kb.as_markup()
