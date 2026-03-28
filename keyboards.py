from aiogram.utils.keyboard import InlineKeyboardBuilder

def game_keyboard(game_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Записатися", callback_data=f"join:{game_id}")
    kb.button(text="❌ Скасувати", callback_data=f"leave:{game_id}")
    kb.button(text="💸 Я оплатив", callback_data=f"paid:{game_id}")
    kb.adjust(1)
    return kb.as_markup()
