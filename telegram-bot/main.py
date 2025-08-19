import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command

load_dotenv()

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 Olá! Eu sou um bot minimalista feito com aiogram v3 🚀")

@router.message()
async def echo(message: types.Message):
    await message.answer(f"Você disse: {message.text}")


async def main():
    bot = Bot(token=TOKEN, parse_mode="MarkdownV2")
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())