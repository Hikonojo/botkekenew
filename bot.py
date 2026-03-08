import asyncio
import time
import os
import random
import logging
from datetime import date
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

TARGET_ID = 800734488 
MUTE_TIME = 5 * 60     
COOLDOWN = 60 * 60     

butilka_cooldowns = {}
butilka_daily = {}
active_duels = {}
# Словарь для хранения побед: {user_id: {"name": "Имя", "wins": 5}}
duel_stats = {}

# --- Функция таймера (вернул 5 секунд) ---
async def run_timer(message: types.Message, base_text: str, duration: int):
    remaining = duration
    interval = 5  # Твои 5 секунд
    
    while remaining > 0:
        await asyncio.sleep(interval)
        remaining -= interval
        if remaining <= 0: break
        
        minutes, seconds = divmod(remaining, 60)
        try:
            await message.edit_text(f"{base_text}\nОсталось: {minutes}:{seconds:02d} 🕒")
        except Exception:
            break
            
    try:
        await message.edit_text(f"{base_text.split('!')[0]} свободен, бутылка опустела! 🎉")
    except Exception:
        pass

# -------------------- LEADERBOARD (/top) --------------------
@dp.message_handler(commands=["top"])
async def show_top(message: types.Message):
    if not duel_stats:
        await message.reply("Таблица лидеров пока пуста. Сначала кто-то должен победить! ⚔️")
        return

    # Сортируем по количеству побед
    sorted_stats = sorted(duel_stats.items(), key=lambda x: x[1]['wins'], reverse=True)
    
    text = "🏆 **ТОП ПОБЕДИТЕЛЕЙ В ДУЭЛЯХ:**\n\n"
    for i, (user_id, info) in enumerate(sorted_stats[:10], 1): # Топ-10
        text += f"{i}. {info['name']} — {info['wins']} побед(ы)\n"
    
    await message.reply(text, parse_mode="Markdown")

# -------------------- DUEL --------------------
@dp.message_handler(commands=["duel"])
async def duel(message: types.Message):
    if not message.reply_to_message:
        await message.reply("Ответь на сообщение того, кого вызываешь!")
        return

    challenger = message.from_user
    target = message.reply_to_message.from_user

    if challenger.id == target.id:
        await message.reply("Сам с собой? Это уже клиника. 🤡")
        return

    duel_id = str(int(time.time()))
    active_duels[duel_id] = {
        "c_id": challenger.id, "t_id": target.id, 
        "c_name": challenger.first_name, "t_name": target.first_name
    }

    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("⚔️ Принять", callback_data=f"d_acc:{duel_id}"),
        InlineKeyboardButton("🏃 Сбежать", callback_data=f"d_dec:{duel_id}")
    )
    await message.reply(f"⚡️ {target.first_name}, тебя вызывает на дуэль {challenger.first_name}!", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("d_"))
async def duel_callback(callback: types.CallbackQuery):
    action, duel_id = callback.data.split(":")
    if duel_id not in active_duels:
        await callback.answer("Дуэль устарела.")
        return

    data = active_duels[duel_id]
    if callback.from_user.id != data["t_id"]:
        await callback.answer("Это не твой вызов!")
        return

    if action == "d_dec":
        await callback.message.edit_text(f"🏃 {data['t_name']} убежал. Бой не состоялся.")
        active_duels.pop(duel_id, None)
    else:
        # Логика принятия
        winner_id, loser_id = random.sample([data["c_id"], data["t_id"]], 2)
        
        # Определяем имена
        if winner_id == data["c_id"]:
            winner_name = data["c_name"]
            loser_name = data["t_name"]
        else:
            winner_name = data["t_name"]
            loser_name = data["c_name"]

        # ОБНОВЛЯЕМ СТАТИСТИКУ
        if winner_id not in duel_stats:
            duel_stats[winner_id] = {"name": winner_name, "wins": 0}
        duel_stats[winner_id]["wins"] += 1
        duel_stats[winner_id]["name"] = winner_name # Обновляем имя, если сменил

        active_duels.pop(duel_id, None)

        try:
            until = int(time.time()) + MUTE_TIME
            await bot.restrict_chat_member(callback.message.chat.id, loser_id, ChatPermissions(can_send_messages=False), until_date=until)
            
            base_text = f"💀 {loser_name} проиграл дуэль и отправлен в бутылку! Победитель: {winner_name} 🍼"
            timer_msg = await callback.message.edit_text(f"{base_text}\nОсталось: 5:00 🕒")
            
            asyncio.create_task(run_timer(timer_msg, base_text, MUTE_TIME))
        except Exception as e:
            await callback.message.edit_text(f"Ошибка при муте: {e}\nПобедил {winner_name}!")

# --- [Остальные команды /butilka и /antibutilka без изменений] ---
