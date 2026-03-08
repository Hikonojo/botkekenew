import asyncio
import time
import os
import random
from datetime import date
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не найден!")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

TARGET_ID = 800734488 
MUTE_TIME = 5 * 60      
COOLDOWN = 60 * 60      

butilka_cooldowns = {}
antibutilka_cooldowns = {}
butilka_daily = {}
active_duels = {}

# --- [Код /butilka и /antibutilka оставляем как есть, они работают] ---

# -------------------- DUEL --------------------
@dp.message_handler(commands=["duel"])
async def duel(message: types.Message):
    # Проверка на ответ на сообщение
    if not message.reply_to_message:
        await message.reply("Ответь на сообщение человека, которого хочешь вызвать на дуэль.")
        return

    challenger = message.from_user
    target = message.reply_to_message.from_user

    if challenger.id == target.id:
        await message.reply("Сам с собой? Это уже клиника. 🤡")
        return

    if target.is_bot:
        await message.reply("Боты не пьют из бутылок, у них нет печени.")
        return

    # Генерируем короткий ID для колбэка
    duel_id = str(random.randint(1000, 9999))
    active_duels[duel_id] = {
        "challenger_id": challenger.id,
        "target_id": target.id,
        "chat_id": message.chat.id,
        "challenger_name": challenger.first_name,
        "target_name": target.first_name
    }

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("⚔️ Принять", callback_data=f"duel_acc:{duel_id}"),
        InlineKeyboardButton("🏃 Сбежать", callback_data=f"duel_dec:{duel_id}")
    )

    await message.reply(
        f"⚡️ {target.first_name}, тебя вызывает на дуэль {challenger.first_name}!\n"
        f"Проигравший отправляется в бутылку на 5 минут.",
        reply_markup=kb
    )

@dp.callback_query_handler(lambda c: c.data.startswith("duel_"))
async def duel_buttons(callback: types.CallbackQuery):
    data_parts = callback.data.split(":")
    if len(data_parts) < 2:
        return
        
    action, duel_id = data_parts
    
    if duel_id not in active_duels:
        await callback.answer("Дуэль протухла или бот перезагрузился. 💀", show_alert=True)
        await callback.message.delete()
        return

    duel_info = active_duels[duel_id]
    
    # Только цель может принять вызов
    if callback.from_user.id != duel_info["target_id"]:
        await callback.answer("Это приглашение не для тебя! 🛑", show_alert=True)
        return

    if action == "duel_dec":
        await callback.message.edit_text(f"🏃 {duel_info['target_name']} трусливо убежал от {duel_info['challenger_name']}.")
        active_duels.pop(duel_id, None)
        return

    if action == "duel_acc":
        # Розыгрыш
        loser_id = random.choice([duel_info["challenger_id"], duel_info["target_id"]])
        loser_name = duel_info["challenger_name"] if loser_id == duel_info["challenger_id"] else duel_info["target_name"]
        
        active_duels.pop(duel_id, None) # Удаляем сразу, чтобы не нажали дважды

        try:
            until_date = int(time.time()) + MUTE_TIME
            await bot.restrict_chat_member(
                chat_id=duel_info["chat_id"],
                user_id=loser_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date
            )

            msg_text = f"💀 {loser_name} проиграл в честном бою и сел на бутылку! 🍼\nОсталось: 5:00"
            timer_msg = await callback.message.edit_text(msg_text)

            # Таймер (создаем задачу в фоне)
            asyncio.create_task(duel_timer_logic(timer_msg, loser_name, MUTE_TIME))

        except Exception as e:
            await callback.message.edit_text(f"Не удалось отправить проигравшего в бутылку: {e}")

async def duel_timer_logic(message, name, remaining):
    while remaining > 0:
        await asyncio.sleep(10) # Обновляем раз в 10 сек, чтобы не ловить лимиты Telegram
        remaining -= 10
        if remaining <= 0: break
        
        minutes, seconds = divmod(remaining, 60)
        try:
            await message.edit_text(f"🍼 {name} всё ещё в бутылке...\nОсталось: {minutes}:{seconds:02d} 🕒")
        except:
            break
    
    try:
        await message.edit_text(f"🎉 {name} выбрался из бутылки и готов к новым свершениям!")
    except:
        pass

# -------------------- RUN --------------------
if __name__ == "__main__":
    # Правильный запуск для aiogram 2.x
    executor.start_polling(dp, skip_updates=True)
