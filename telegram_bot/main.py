import asyncio
import logging
import os
import sys
import os.path
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command, CommandObject
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
from instant_view import generate_telegraph, init_telegraph
from shared.ai_tools import GROQ_API, GOOGLE_IMAGE_API
from utils import transcribe_media, send_image_with_button, send_media_stream, is_valid_link, VideoNotFound

# Add the root directory to the path so we can import the database module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import History

load_dotenv()

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
router = Router()


@router.message(Command("image"))
async def cmd_image(message: types.Message, command: CommandObject):
    if not command.args:
        await message.reply("Por favor, forneça uma consulta para a imagem. Exemplo: /image cachorro")
        return
    await send_image_with_button(message, command.args)


@router.message(F.text.contains('@'))
async def mention_handler(message: types.Message):
    # Check if the message is a mention of the bot
    bot_username = (await message.bot.get_me()).username
    if bot_username not in message.text:
        return

    if message.text:
        try:
            response = GROQ_API.chat(message.text)
            await message.reply(response)
        except Exception as e:
            logging.error(f"Error processing mention: {e}")
            await message.reply("Desculpe, ocorreu um erro ao processar sua solicitação.")


@router.callback_query(F.data.startswith("another_image:"))
async def callback_another_image(callback: types.CallbackQuery):
    query = callback.data.split(":", 1)[1]
    # Send another image with the same query
    await send_image_with_button(callback.message, query)
    # Answer the callback query to remove the loading state
    await callback.answer()


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


@router.message(F.text)
async def text_handler(message: types.Message):
    if len(message.text.split(' ')) > 1:
        return

    logging.info(f"IsValidLink: {is_valid_link(message.text)}")
    try:
        if 'https://' in message.text and is_valid_link(message.text):
            await send_media_stream(message)

    except VideoNotFound as e:
        if 'https://x.com/' and '/status/' in message.text:
            url = await generate_telegraph(message.text)
            await message.reply(url)

# Message handlers for saving messages to history
@router.message()
async def save_message_to_history(message: types.Message, bot: Bot):
    """Save all messages to the history database."""
    # Get the history object from the bot's data
    history = bot.get('history')
    
    if not history:
        return
    
    # Determine if the message is from the bot itself
    from_bot = message.from_user.id == bot.id if message.from_user else False
    
    # Get replied_to message ID if it exists
    replied_to = str(message.reply_to_message.message_id) if message.reply_to_message else None
    
    # Save the message to the database
    history.save_message(
        user=str(message.from_user.username or message.from_user.id) if message.from_user else "Unknown",
        message_id=str(message.message_id),
        text=message.text or "",
        replied_to=replied_to,
        from_bot=from_bot
    )


async def main():
    await init_telegraph()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher()
    dp.include_router(router)
    
    # Initialize message history database
    history = History()
    
    # Store history object in the bot's data for access in handlers
    dp['history'] = history
    bot['history'] = history
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())