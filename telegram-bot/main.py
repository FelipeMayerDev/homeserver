import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from ai_tools import GROQ_API, GOOGLE_IMAGE_API
from utils import transcribe_media, search_and_send_image

load_dotenv()

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
router = Router()


@router.message(Command("image"))
async def cmd_image(message: types.Message):
    command_parts = message.text.split(" ", 1)
    if not command_parts:
        return
    await search_and_send_image(message, command_parts)


@router.message(F.video)
async def video_handler(message: types.Message, bot: Bot):
    await transcribe_media(message, bot, "video", message.video.file_id, "mp4")


@router.message(F.video_note)
async def video_note_handler(message: types.Message, bot: Bot):
    await transcribe_media(message, bot, "video_note", message.video_note.file_id, "mp4")


@router.message(F.audio)
async def audio_handler(message: types.Message, bot: Bot):
    await transcribe_media(message, bot, "audio", message.audio.file_id, "mp3")


@router.message(F.voice)
async def voice_handler(message: types.Message, bot: Bot):
    await transcribe_media(message, bot, "voice", message.voice.file_id, "ogg")


# @router.message(F.text)
# async def echo(message: types.Message):
#     pass


async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='MarkdownV2'))
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())