import asyncio
import time
import os
import random
import logging
from datetime import date
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton

# Включаем логирование, чтобы видеть ошибки в панели Railway
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не найден! Проверь Shared Variable в Railway")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

TARGET_ID = 800734488  # BUNKERKlNG
MUTE_TIME = 5 * 60      # 5 минут
COOLDOWN = 60 * 60      # 1 час

# Хранилища
butilka_cooldowns = {}
antibutilka_cooldowns = {}
butilka_daily = {}
active_duels = {}

# -------------------- DUEL (ТЕПЕРЬ ПЕРВАЯ) --------------------
@dp.message_handler(commands=["duel"])
async def duel(message: types.Message):
    # Эта строчка ОБЯЗАНА появиться в логах Railway при команде
    print(f"!!! КТО-ТО ВЫЗВАЛ ДУЭЛЬ !!! От: {message.from_user.id}")

    if not message.reply_to_message:
        await message.reply("Ответь на сообщение того, кого хочешь вызвать!")
        return

    challenger = message.from_user
    target = message.reply_to_message.from_user

    if challenger.id == target.id:
        await message.reply("Шизофрения — это когда вызываешь на дуэль сам себя. 🤡")
        return

    duel_id = str(int(time.time())) + str(random.randint(10, 99))
    active_duels[duel_id] = {
        "c_id": challenger.id, 
        "t_id": target.id, 
        "chat_id": message.chat.id,
        "c_name": challenger.first_name,
        "t_name": target.first_name
    }

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("⚔️ Принять", callback_data=f"d_acc:{duel_id}"),
        InlineKeyboardButton("🏃 Сбежать", callback_data=f"d_dec:{duel_id}")
    )

    await message.reply(f"⚡️ {target.first_name}, тебя вызывает на дуэль {challenger.first_name}!", reply_markup=kb)

# -------------------- ОБРАБОТКА КНОПОК ДУЭЛИ --------------------
@dp.callback_query_handler(lambda c: c.data.startswith("d_"))
async def duel_callback(callback: types.CallbackQuery):
    action, duel_id = callback.data.split(":")
    
    if duel_id not in active_duels:
        await callback.answer("Дуэль не найдена или устарела.", show_alert=True)
        return

    data = active_duels[duel_id]

    if callback.from_user.id != data["t_id"]:
        await callback.answer("Это не твой вызов!", show_alert=True)
        return

    if action == "d_dec":
        await callback.message.edit_text(f"🏃 {data['t_name']} испугался и убежал.")
        active_duels.pop(duel_id, None)
        return

    # Если приняли
    winner_id, loser_id = random.sample([data["c_id"], data["t_id"]], 2)
    loser_name = data["c_name"] if loser_id == data["c_id"] else data["t_name"]
    
    active_duels.pop(duel_id, None)

    try:
        until = int(time.time()) + MUTE_TIME
        await bot.restrict_chat_member(data["chat_id"], loser_id, ChatPermissions(can_send_messages=False), until_date=until)
        await callback.message.edit_text(f"💀 {loser_name} проиграл дуэль и отправлен в бутылку на 5 минут! 🍼")
    except Exception as e:
        await callback.message.edit_text(f"Дуэль прошла, но замутить не вышло: {e}")

# -------------------- BUTILKA --------------------
@dp.message_handler(commands=["butilka"])
async def butilka(message: types.Message):
    user_id = message.from_user.id
    now = time.time()
    chat_id = message.chat.id

    today = date.today().isoformat()
    if user_id not in butilka_daily or butilka_daily[user_id]["date"] != today:
        butilka_daily[user_id] = {"date": today, "count": 0}

    if butilka_daily[user_id]["count"] >= 3:
        await message.reply("3/3 на сегодня. Хватит.")
        return

    if user_id in butilka_cooldowns and now - butilka_cooldowns[user_id] < COOLDOWN:
        rem = int((COOLDOWN - (now - butilka_cooldowns[user_id])) / 60)
        await message.reply(f"Жди {rem} мин.")
        return

    try:
        await bot.restrict_chat_member(chat_id, TARGET_ID, ChatPermissions(can_send_messages=False), until_date=int(time.time() + MUTE_TIME))
        butilka_daily[user_id]["count"] += 1
        butilka_cooldowns[user_id] = now
        await message.reply(f"@BUNKERKlNG в бутылке! 🍼 ({butilka_daily[user_id]['count']}/3)")
    except Exception as e:
        await message.reply(f"Ошибка: {e}")

# -------------------- ANTIBUTILKA --------------------
@dp.message_handler(commands=["antibutilka"])
async def antibutilka(message: types.Message):
    try:
        await bot.restrict_chat_member(
            message.chat.id, TARGET_ID, 
            ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True),
            until_date=0
        )
        await message.reply("Свободу попугаям! @BUNKERKlNG размучен. 🎈")
    except Exception as e:
        await message.reply(f"Не вышло: {e}")

# -------------------- ЗАПУСК --------------------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
