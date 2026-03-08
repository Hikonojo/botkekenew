import asyncio
import time
from datetime import date
from aiogram import Bot, Dispatcher, types
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
import os
import random

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не найден! Проверь Shared Variable в Railway")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

TARGET_ID = 800734488  # BUNKERKlNG
MUTE_TIME = 5 * 60      # 5 минут
COOLDOWN = 60 * 60      # 1 час

# Кулдауны и счётчики
butilka_cooldowns = {}
antibutilka_cooldowns = {}
butilka_daily = {}

# Активные дуэли
active_duels = {}

# -------------------- BUTILKA --------------------
@dp.message_handler(commands=["butilka"])
async def butilka(message: types.Message):
    user_id = message.from_user.id
    now = time.time()
    chat_id = message.chat.id

    today = date.today().isoformat()
    info = butilka_daily.get(user_id)
    if info is None or info.get("date") != today:
        butilka_daily[user_id] = {"date": today, "count": 0}

    if butilka_daily[user_id]["count"] >= 3:
        await message.reply("Ты уже использовал 3/3 сегодня. Завтра попробуй снова.")
        return

    if user_id in butilka_cooldowns and now - butilka_cooldowns[user_id] < COOLDOWN:
        remaining = int((COOLDOWN - (now - butilka_cooldowns[user_id])) / 60)
        await message.reply(f"Кулдаун, терпила. Жди ещё {remaining} мин.")
        return

    try:
        member = await bot.get_chat_member(chat_id, TARGET_ID)
    except Exception as e:
        await message.reply(f"Не могу получить информацию о пользователе: {e}")
        return

    if member.is_chat_admin():
        await message.reply("Эй, @BUNKERKlNG слишком крут для бутылки, он админ 😎")
        return

    butilka_daily[user_id]["count"] += 1
    butilka_cooldowns[user_id] = now
    used = butilka_daily[user_id]["count"]

    until_date = int(time.time()) + MUTE_TIME

    try:
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=TARGET_ID,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )

        timer_msg = await message.reply(f"@BUNKERKlNG отправлен в бутылку на 5 минут 🍼 ({used}/3)\nОсталось: 5:00 🕒")

        async def timer():
            remaining = MUTE_TIME
            interval = 5
            while remaining > 0:
                minutes, seconds = divmod(int(remaining), 60)
                try:
                    await timer_msg.edit_text(f"@BUNKERKlNG в бутылке 🍼 ({used}/3)\nОсталось: {minutes}:{seconds:02d} 🕒")
                except:
                    pass
                await asyncio.sleep(interval)
                remaining -= interval
            try:
                await timer_msg.edit_text(f"@BUNKERKlNG свободен, бутылка опустела 🎉")
            except:
                pass

        asyncio.create_task(timer())

    except Exception as e:
        await message.reply(f"Бот не админ или не может мутить. Ошибка: {e}")

# -------------------- ANTIBUTILKA --------------------
@dp.message_handler(commands=["antibutilka"])
async def antibutilka(message: types.Message):
    user_id = message.from_user.id
    now = time.time()
    chat_id = message.chat.id

    if user_id in antibutilka_cooldowns and now - antibutilka_cooldowns[user_id] < COOLDOWN:
        remaining = int((COOLDOWN - (now - antibutilka_cooldowns[user_id])) / 60)
        await message.reply(f"Кулдаун для /antibutilka. Жди ещё {remaining} мин.")
        return

    try:
        member = await bot.get_chat_member(chat_id, TARGET_ID)
    except Exception as e:
        await message.reply(f"Не могу получить информацию о пользователе: {e}")
        return

    if member.is_chat_admin():
        await message.reply("Он и так админ — проблем нет.")
        return

    try:
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=TARGET_ID,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            ),
            until_date=0
        )
        antibutilka_cooldowns[user_id] = now
        await message.reply(f"@BUNKERKlNG освобождён из бутылки 🎈")
    except Exception as e:
        await message.reply(f"Не могу снять мут. Ошибка: {e}")

# -------------------- DUEL --------------------
@dp.message_handler(commands=["duel"])
async def duel(message: types.Message):
    if not message.reply_to_message:
        await message.reply("Ответь на сообщение человека, которого хочешь вызвать на дуэль.")
        return

    challenger = message.from_user
    target = message.reply_to_message.from_user

    if challenger.id == target.id:
        await message.reply("Сам с собой дуэль? Шизофрения, конечно, мощная.")
        return

    if target.is_bot:
        await message.reply("Ботов на дуэль не вызывают.")
        return

    duel_id = str(time.time())
    active_duels[duel_id] = (challenger.id, target.id, message.chat.id)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("⚔️ Принять", callback_data=f"duel_accept:{duel_id}"),
        InlineKeyboardButton("🏃 Отказаться", callback_data=f"duel_decline:{duel_id}")
    )

    await message.reply(f"{target.first_name}, тебя вызывает на дуэль {challenger.first_name} ⚔️", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("duel_"))
async def duel_buttons(callback: types.CallbackQuery):
    await callback.answer()  # обязательно для кнопок

    action, duel_id = callback.data.split(":")
    if duel_id not in active_duels:
        await callback.message.edit_text("Эта дуэль уже закончилась.")
        return

    challenger_id, target_id, chat_id = active_duels[duel_id]

    if callback.from_user.id != target_id:
        await callback.answer("Это не твоя дуэль.")
        return

    if action == "duel_decline":
        await callback.message.edit_text(f"{callback.from_user.first_name} трусливо избежал дуэли 🏃")
        del active_duels[duel_id]
        return

    if action == "duel_accept":
        loser = random.choice([challenger_id, target_id])
        loser_name = "Вызывающий" if loser == challenger_id else "Принявший"
        until_date = int(time.time()) + MUTE_TIME

        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=loser,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date
            )

            timer_msg = await callback.message.edit_text(f"{loser_name} проиграл дуэль и отправляется в бутылку на 5 минут 🍼\nОсталось: 5:00 🕒")

            async def duel_timer():
                remaining = MUTE_TIME
                interval = 5
                while remaining > 0:
                    minutes, seconds = divmod(int(remaining), 60)
                    try:
                        await timer_msg.edit_text(f"{loser_name} в бутылке 🍼\nОсталось: {minutes}:{seconds:02d} 🕒")
                    except:
                        pass
                    await asyncio.sleep(interval)
                    remaining -= interval
                try:
                    await timer_msg.edit_text(f"{loser_name} свободен, бутылка опустела 🎉")
                except:
                    pass

            asyncio.create_task(duel_timer())

        except Exception as e:
            await callback.message.edit_text(f"Не смог замутить. Ошибка: {e}")

        del active_duels[duel_id]

# -------------------- RUN --------------------
if __name__ == "__main__":
    asyncio.run(dp.start_polling())