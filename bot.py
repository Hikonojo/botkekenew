import asyncio
import time
from datetime import date
from aiogram import Bot, Dispatcher, types
from aiogram.types import ChatPermissions
import os

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не найден! Проверь Shared Variable в Railway")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

TARGET_ID = 800734488  # BUNKERKlNG
MUTE_TIME = 5 * 60      # 5 минут
COOLDOWN = 60 * 60      # 1 час

# Кулдауны и счётчики
butilka_cooldowns = {}        # user_id : last_use_time для /butilka
antibutilka_cooldowns = {}    # user_id : last_use_time для /antibutilka
butilka_daily = {}            # user_id : {'date': 'YYYY-MM-DD', 'count': n}

@dp.message_handler(commands=["butilka"])
async def butilka(message: types.Message):
    user_id = message.from_user.id
    now = time.time()
    chat_id = message.chat.id

    # дневной лимит (3 в день)
    today = date.today().isoformat()
    info = butilka_daily.get(user_id)
    if info is None or info.get("date") != today:
        butilka_daily[user_id] = {"date": today, "count": 0}

    if butilka_daily[user_id]["count"] >= 3:
        await message.reply("Ты уже использовал 3/3 сегодня. Завтра попробуй снова.")
        return

    # проверка кулдауна (час)
    if user_id in butilka_cooldowns and now - butilka_cooldowns[user_id] < COOLDOWN:
        remaining = int((COOLDOWN - (now - butilka_cooldowns[user_id])) / 60)
        await message.reply(f"Кулдаун, терпила. Жди ещё {remaining} мин.")
        return

    # проверяем, админ ли цель
    try:
        member = await bot.get_chat_member(chat_id, TARGET_ID)
    except Exception as e:
        await message.reply(f"Не могу получить информацию о пользователе: {e}")
        return

    if member.is_chat_admin():
        await message.reply("Эй, @BUNKERKlNG слишком крут для бутылки, он админ 😎")
        return

    # всё ок — увеличиваем счётчик и ставим кулдаун
    butilka_daily[user_id]["count"] += 1
    butilka_cooldowns[user_id] = now
    used = butilka_daily[user_id]["count"]

    until_date = int(time.time()) + MUTE_TIME

    try:
        # мутим цель
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=TARGET_ID,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )

        # первое сообщение с таймером и счётчиком использования
        timer_msg = await message.reply(f"@BUNKERKlNG отправлен в бутылку на 5 минут 🍼 ({used}/3)\nОсталось: 5:00 🕒")

        # таймер обновляем каждые 5 секунд
        interval = 5
        remaining = MUTE_TIME
        while remaining > 0:
            minutes, seconds = divmod(int(remaining), 60)
            await timer_msg.edit_text(f"@BUNKERKlNG в бутылке 🍼 ({used}/3)\nОсталось: {minutes}:{seconds:02d} 🕒")
            await asyncio.sleep(interval)
            remaining -= interval
            if remaining < 0:
                remaining = 0

        await timer_msg.edit_text(f"@BUNKERKlNG свободен, бутылка опустела 🎉")

    except Exception as e:
        await message.reply(f"Бот не админ или не может мутить. Я не бог, блин.\nОшибка: {e}")

@dp.message_handler(commands=["antibutilka"])
async def antibutilka(message: types.Message):
    user_id = message.from_user.id
    now = time.time()
    chat_id = message.chat.id

    # проверка кулдауна для /antibutilka
    if user_id in antibutilka_cooldowns and now - antibutilka_cooldowns[user_id] < COOLDOWN:
        remaining = int((COOLDOWN - (now - antibutilka_cooldowns[user_id])) / 60)
        await message.reply(f"Кулдаун для /antibutilka. Жди ещё {remaining} мин.")
        return

    # получим статус цели (чтобы, например, не пытаться "освободить" админа)
    try:
        member = await bot.get_chat_member(chat_id, TARGET_ID)
    except Exception as e:
        await message.reply(f"Не могу получить информацию о пользователе: {e}")
        return

    if member.is_chat_admin():
        await message.reply("Он и так админ — проблем нет.")
        return

    try:
        # Снимаем ограничения (разрешаем отправлять сообщения и пр.)
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
        await message.reply(f"Не могу снять мут. Я снова не бог.\nОшибка: {e}")

if __name__ == "__main__":
    asyncio.run(dp.start_polling())