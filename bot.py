"""Точка входу: python bot.py"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from db import Database
from handlers import admin, booking, common


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(name)s  %(message)s", datefmt="%H:%M:%S")
    config = load_config()

    db = Database(config.db_path)
    db.init()

    bot = Bot(config.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    # db і config автоматично передаються в обробники як аргументи з такими самими іменами
    dp = Dispatcher(storage=MemoryStorage(), db=db, config=config)
    # Порядок важливий: common містить обробники «на все інше», тому він останній
    dp.include_routers(admin.router, booking.router, common.router)

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот запущено. Зупинити: Ctrl+C")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
