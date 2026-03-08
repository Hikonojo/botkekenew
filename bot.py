import asyncio
import time
import os
import random
import logging
from datetime import date
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton

# Настройка логов, чтобы видеть ошибки в Railway
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не найден!")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

TARGET_ID = 800734488 
MUTE_TIME = 5 * 60     
COOLDOWN = 60 * 60     

butilka_cooldowns = {}
butilka_daily = {}
active_duels = {}
# Данные о победах
duel_stats = {}

# --- Функция таймера (5 секунд) ---
async def run_timer(message: types.Message, base_text: str, duration: int):
    remaining = duration
    interval = 5 
    while remaining > 0:
        await asyncio.sleep(interval)
        remaining -= interval
        if remaining <= 0: break
        minutes, seconds = divmod(remaining, 60)
        try:
            await message.edit_text(f"{base_text}\nОсталось: {minutes}:{seconds:02d} 🕒")
        except:
            break
    try:
        await message.edit_text(f"{base_text.split('!')[0]} свободен, бутылка опустела! 🎉")
    except:
        pass

# -------------------- ТОП ЛИДЕРОВ --------------------
@dp.message_handler(commands=["top"])
async def show_top(message: types.Message):
    if not duel_stats:
        await message.reply("🏆 Таблица лидеров пока пуста. Победите в дуэли, чтобы стать первым!")
        return

    sorted_stats = sorted(duel_stats.items(), key=lambda x: x[1]['wins'], reverse=True)
    text = "🏆 **ТОП ПОБЕДИТЕЛЕЙ:**\n\n"
    for i, (user_id, info) in enumerate(sorted_stats[:10], 1):
        text += f"{i}. {info['name']} — {info['wins']} ⚔️\n"
    
    await message.reply(text, parse_mode="Markdown")

# -------------------- ДУЭЛЬ --------------------
@dp.message_handler(commands=["duel"])
async def duel(message: types.Message):
    if not message.reply_to_message:
        await message.reply("Ответь на сообщение того, кого вызываешь на дуэль!")
        return

    challenger = message.from_user
    target = message.reply_to_message.from_user

    if challenger.id == target.id:
        await message.reply("Нельзя вызвать на дуэль самого себя! 🤡")
        return

    duel_id = str(int(time.time()))
    active_duels[duel_id] = {
        "c_id": challenger.id, "t_id": target.id, 
        "c_name": challenger.first_name, "t_name": target.first_name,
        "chat_id": message.chat.id
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
        await callback.answer("Дуэль не найдена.")
        return

    data = active_duels[duel_id]
    if callback.from_user.id != data["t_id"]:
        await callback.answer("Это не твой вызов!")
        return

    if action == "d_dec":
        await callback.message.edit_text(f"🏃 {data['t_name']} испугался и убежал.")
        active_duels.pop(duel_id, None)
    else:
        winner_id, loser_id = random.sample([data["c_id"], data["t_id"]], 2)
        winner_name = data["c_name"] if winner_id == data["c_id"] else data["t_name"]
        loser_name = data["t_name"] if winner_id == data["c_id"] else data["c_name"]

        # Запись статистики
        if winner_id not in duel_stats:
            duel_stats[winner_id] = {"wins": 0}
        duel_stats[winner_id]["wins"] += 1
        duel_stats[winner_id]["name"] = winner_name

        active_duels.pop(duel_id, None)

        try:
            until = int(time.time()) + MUTE_TIME
            await bot.restrict_chat_member(data["chat_id"], loser_id, ChatPermissions(can_send_messages=False), until_date=until)
            
            base_text = f"💀 {loser_name} проиграл дуэль! Победитель: {winner_name} 🍼"
            timer_msg = await callback.message.edit_text(f"{base_text}\nОсталось: 5:00 🕒")
            asyncio.create_task(run_timer(timer_msg, base_text, MUTE_TIME))
        except Exception as e:
            await callback.message.edit_text(f"Победил {winner_name}, но мут не удался: {e}")

# -------------------- BUTILKA --------------------
@dp.message_handler(commands=["butilka"])
async def butilka(message: types.Message):
    user_id = message.from_user.id
    today = date.today().isoformat()
    
    if user_id not in butilka_daily or butilka_daily[user_id]["date"] != today:
        butilka_daily[user_id] = {"date": today, "count": 0}

    if butilka_daily[user_id]["count"] >= 3:
        await message.reply("Лимит 3/3 на сегодня!")
        return

    try:
        await bot.restrict_chat_member(message.chat.id, TARGET_ID, ChatPermissions(can_send_messages=False), until_date=int(time.time() + MUTE_TIME))
        butilka_daily[user_id]["count"] += 1
        
        base_text = f"🍼 @BUNKERKlNG в бутылке! ({butilka_daily[user_id]['count']}/3)"
        timer_msg = await message.reply(f"{base_text}\nОсталось: 5:00 🕒")
        asyncio.create_task(run_timer(timer_msg, base_text, MUTE_TIME))
    except Exception as e:
        await message.reply(f"Ошибка: {e}")

# -------------------- ANTIBUTILKA --------------------
@dp.message_handler(commands=["antibutilka"])
async def antibutilka(message: types.Message):
    try:
        await bot.restrict_chat_member(message.chat.id, TARGET_ID, ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True), until_date=0)
        await message.reply("🔓 @BUNKERKlNG размучен!")
    except Exception as e:
        await message.reply(f"Ошибка: {e}")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
