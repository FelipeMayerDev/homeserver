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
from utils import transcribe_media, send_image_with_button, send_media_stream, is_valid_link, VideoNotFound, process_youtube_video
from shared.database import History

load_dotenv()

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
router = Router()


@router.message(Command("image"))
async def cmd_image(message: types.Message, command: CommandObject):
    if not command.args:
        await message.reply("Por favor, forneça uma consulta para a imagem. Exemplo: /image cachorro")
        return
    response = await send_image_with_button(message, command.args)
    save_message_to_history(message, message.bot)


@router.message(Command("resume"))
async def cmd_resume(message: types.Message, command: CommandObject):
    if not command.args:
        await message.reply("Por favor, forneça um link de um vídeo do YouTube. Exemplo: /resume https://www.youtube.com/watch?v=example")
        return
    
    # Check if it's a valid YouTube link
    if "youtube.com" not in command.args and "youtu.be" not in command.args:
        await message.reply("Por favor, forneça um link válido do YouTube.")
        return
    
    try:
        # Process the YouTube video
        processing_message = await message.reply("Processando seu vídeo...")
        summary = await process_youtube_video(command.args)
        await processing_message.edit_text(f"📝 <b>Resumo do vídeo:</b>\n\n{summary}", parse_mode="HTML")
        save_message_to_history(message, message.bot)
    except Exception as e:
        logging.error(f"Error processing YouTube video: {e}")
        await message.reply("Desculpe, ocorreu um erro ao processar o vídeo.")


@router.message(Command("tldr"))
async def cmd_tldr(message: types.Message, command: CommandObject):
    try:
        # Get message limit (default 100)
        limit = int(command.args) if command.args and command.args.isdigit() else 100
        limit = min(limit, 300)  # maximum 300 messages
        
        processing_message = await message.reply("🔄 Analisando mensagens...")
        
        history = History()
        if not history:
            await processing_message.edit_text("❌ Erro ao acessar histórico de mensagens.")
            return
            
        messages = history.get_all_messages(limit)
        
        if not messages:
            await processing_message.edit_text("❌ Não há mensagens no histórico.")
            return
        
        conversation, stats = prepare_messages_for_tldr(messages)
        
        if not conversation.strip():
            stats_text = format_tldr_stats(stats)
            await processing_message.edit_text(f"❌ Não há mensagens de texto válidas para resumir.{stats_text}", parse_mode="HTML")
            return
        
        # Generate AI summary
        prompt = f"Faça um resumo conciso das principais discussões desta conversa em português:\n\n{conversation}"
        summary = GROQ_API.chat(prompt)
        
        if not summary or summary.strip() == "":
            await processing_message.edit_text("❌ Erro ao gerar resumo com IA.")
            return
        
        # Format response with statistics
        stats_text = format_tldr_stats(stats)
        response = f"📝 <b>Resumo da conversa:</b>\n\n{summary}{stats_text}"
        
        # Telegram message limit is 4096 characters
        if len(response) > 4000:
            response = response[:3900] + "...\n\n[Mensagem truncada]"
        
        await processing_message.edit_text(response, parse_mode="HTML")
        save_message_to_history(message, message.bot)
        
    except ValueError:
        await processing_message.edit_text("❌ Número inválido. Use: /tldr ou /tldr [número]")
    except Exception as e:
        logging.error(f"Error generating TLDR: {e}")
        await processing_message.edit_text("❌ Erro ao gerar resumo.")


def prepare_messages_for_tldr(messages, max_chars=4000):
    """Filters and prepares messages for summary, returning text and statistics."""
    filtered = []
    stats = {
        'total_messages': len(messages),
        'media_ignored': 0,
        'bots_ignored': 0,
        'links_ignored': 0,
        'commands_ignored': 0,
        'short_ignored': 0,
        'emoji_ignored': 0,
        'oldest_message': None
    }
    
    for msg in reversed(messages):  # most recent first
        # Handle potential database schema variations
        if len(msg) < 7:
            stats['media_ignored'] += 1
            continue
            
        user, message_id, text, replied_to, from_bot, kind, created = msg
        
        # Skip if it's from a bot
        if from_bot:
            stats['bots_ignored'] += 1
            continue
            
        # Skip if not text (media)
        if not text or kind != "text":
            stats['media_ignored'] += 1
            continue
            
        # Skip very short messages
        if len(text.strip()) < 5:
            stats['short_ignored'] += 1
            continue
            
        # Skip commands
        if text.startswith('/'):
            stats['commands_ignored'] += 1
            continue
            
        # Skip links
        if 'http' in text.lower():
            stats['links_ignored'] += 1
            continue
            
        # Skip if only mentions/emojis
        if text.startswith('@') or len(text.replace(' ', '')) < 3:
            stats['emoji_ignored'] += 1
            continue
            
        # Skip messages with too many emoji/special characters
        if len(text) > 0:  # Prevent division by zero
            alpha_ratio = sum(c.isalnum() or c.isspace() for c in text) / len(text)
            if alpha_ratio < 0.6:
                stats['emoji_ignored'] += 1
                continue
        
        # Valid message - add to filtered list
        filtered.append(f"{user}: {text}")
        
        # Mark first included message (oldest)
        if stats['oldest_message'] is None:
            stats['oldest_message'] = (user, created)
    
    # Truncate by characters if necessary
    conversation = "\n".join(filtered)
    if len(conversation) > max_chars:
        conversation = conversation[:max_chars] + "..."
    
    return conversation, stats


def format_tldr_stats(stats):
    """Formats the summary statistics."""
    total_ignored = (stats['media_ignored'] + stats['bots_ignored'] + 
                    stats['links_ignored'] + stats['commands_ignored'] + 
                    stats['short_ignored'] + stats['emoji_ignored'])
    
    stats_text = f"\n\n📊 <b>Estatísticas:</b>\n"
    stats_text += f"• {stats['total_messages']} mensagens analisadas\n"
    stats_text += f"• {total_ignored} ignoradas ({stats['media_ignored']} mídias, {stats['bots_ignored']} bots, etc.)\n"
    
    if stats['oldest_message']:
        user, created = stats['oldest_message']
        # Format timestamp more readably
        from datetime import datetime
        try:
            # Handle different timestamp formats
            if 'T' in created:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(created, '%Y-%m-%d %H:%M:%S')
            formatted_time = dt.strftime('%d/%m %H:%M')
        except Exception:
            # Fallback to raw timestamp if parsing fails
            formatted_time = str(created)[:16] if created else "Unknown"
        stats_text += f"• Resumo desde: {formatted_time} ({user})"
    
    return stats_text


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
            save_message_to_history(message, message.bot)
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
    save_message_to_history(callback.message, callback.message.bot)


@router.message(F.video)
async def video_handler(message: types.Message, bot: Bot):
    await transcribe_media(message, bot, "video", message.video.file_id, "mp4")
    save_message_to_history(message, bot)


@router.message(F.video_note)
async def video_note_handler(message: types.Message, bot: Bot):
    await transcribe_media(message, bot, "video_note", message.video_note.file_id, "mp4")
    save_message_to_history(message, bot)


@router.message(F.audio)
async def audio_handler(message: types.Message, bot: Bot):
    await transcribe_media(message, bot, "audio", message.audio.file_id, "mp3")
    save_message_to_history(message, bot)


@router.message(F.voice)
async def voice_handler(message: types.Message, bot: Bot):
    await transcribe_media(message, bot, "voice", message.voice.file_id, "ogg")
    save_message_to_history(message, bot)


@router.message(F.text)
async def text_handler(message: types.Message, bot: Bot):
    save_message_to_history(message, bot)
    
    if len(message.text.split(' ')) > 1:
        return

    logging.info(f"IsValidLink: {is_valid_link(message.text)}")
    try:
        if 'https://' in message.text and is_valid_link(message.text):
            await send_media_stream(message)

    except VideoNotFound as e:
        if 'https://x.com/' in message.text and '/status/' in message.text:
            url = await generate_telegraph(message.text)
            await message.reply(url)


def save_message_to_history(message: types.Message, bot: Bot) -> None:
    """Save all messages to the history database."""
    try:
        history = History()
        if not history:
            logging.error("Failed to initialize History database")
            return
        
        # Determine if the message is from the bot itself
        from_bot = message.from_user.id == bot.id if message.from_user else False
        
        # Get replied_to message ID if it exists
        replied_to = str(message.reply_to_message.message_id) if message.reply_to_message else None
        
        # Determine message kind
        kind = None
        if message.text:
            kind = "text"
        elif message.photo:
            kind = "photo"
        elif message.video:
            kind = "video"
        elif message.audio:
            kind = "audio"
        elif message.voice:
            kind = "voice"
        elif message.document:
            kind = "document"
        elif message.sticker:
            kind = "sticker"
        elif message.video_note:
            kind = "video_note"
        
        # Save the message to the database
        history.save_message(
            user=str(message.from_user.username or message.from_user.id) if message.from_user else "Unknown",
            message_id=str(message.message_id),
            text=message.text or "",
            replied_to=replied_to,
            from_bot=from_bot,
            kind=kind
        )
        logging.info(f"Message {message.message_id} saved to history")
    except Exception as e:
        logging.error(f"Error saving message to history: {e}")


async def main():
    await init_telegraph()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())