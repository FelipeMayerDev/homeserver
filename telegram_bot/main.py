import asyncio
import json
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
from shared.ai_tools import Z_AI_API
from utils import transcribe_media, send_image_with_button, send_media_stream, is_valid_link, VideoNotFound, process_youtube_video
from shared.database import History

load_dotenv()

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS_FILE = os.path.join(os.path.dirname(__file__), "allowed_users.json")
router = Router()

# Track consecutive messages per user
consecutive_messages = {}
last_user = None


def load_allowed_users():
    """Load the list of allowed users from JSON file."""
    try:
        with open(ALLOWED_USERS_FILE, 'r') as f:
            data = json.load(f)
            return set(data.get('allowed_users', []))
    except Exception as e:
        logging.error(f"Error loading allowed users: {e}")
        return {'Fockytheguy'}


def save_allowed_users(allowed_users):
    """Save the list of allowed users to JSON file."""
    try:
        with open(ALLOWED_USERS_FILE, 'w') as f:
            json.dump({'allowed_users': list(allowed_users)}, f, indent=4)
        return True
    except Exception as e:
        logging.error(f"Error saving allowed users: {e}")
        return False


def is_user_allowed(username):
    """Check if a user is allowed to use the bot."""
    if not username:
        return False
    allowed_users = load_allowed_users()
    return username in allowed_users


@router.message(Command("image"))
async def cmd_image(message: types.Message, command: CommandObject):
    if not command.args:
        await message.reply("Por favor, forneça uma consulta para a imagem. Exemplo: /image cachorro")
        return
    response = await send_image_with_button(message, command.args)
    save_message_to_history(message, message.bot)


@router.message(Command("add_user"))
async def cmd_add_user(message: types.Message, command: CommandObject):
    """Add a user to the allowed users list."""
    # Only allow Fockytheguy to add users
    if message.from_user.username != "Fockytheguy":
        await message.reply("❌ Apenas o @Fockytheguy pode adicionar usuários.")
        return

    if not command.args:
        await message.reply("Por favor, forneça o username. Exemplo: /add_user @nome_do_usuario")
        return

    # Clean the username (remove @ if present)
    username = command.args.strip().lstrip('@')

    if not username:
        await message.reply("❌ Username inválido.")
        return

    allowed_users = load_allowed_users()

    if username in allowed_users:
        await message.reply(f"❌ O usuário @{username} já está na lista de permitidos.")
        return

    allowed_users.add(username)

    if save_allowed_users(allowed_users):
        await message.reply(f"✅ Usuário @{username} adicionado à lista de permitidos.")
    else:
        await message.reply("❌ Erro ao salvar a lista de usuários.")


@router.message(Command("remove_user"))
async def cmd_remove_user(message: types.Message, command: CommandObject):
    """Remove a user from the allowed users list."""
    # Only allow Fockytheguy to remove users
    if message.from_user.username != "Fockytheguy":
        await message.reply("❌ Apenas o @Fockytheguy pode remover usuários.")
        return

    if not command.args:
        await message.reply("Por favor, forneça o username. Exemplo: /remove_user @nome_do_usuario")
        return

    # Clean the username (remove @ if present)
    username = command.args.strip().lstrip('@')

    if not username:
        await message.reply("❌ Username inválido.")
        return

    allowed_users = load_allowed_users()

    if username not in allowed_users:
        await message.reply(f"❌ O usuário @{username} não está na lista de permitidos.")
        return

    # Prevent removing the owner
    if username == "Fockytheguy":
        await message.reply("❌ Você não pode remover o @Fockytheguy da lista.")
        return

    allowed_users.remove(username)

    if save_allowed_users(allowed_users):
        await message.reply(f"✅ Usuário @{username} removido da lista de permitidos.")
    else:
        await message.reply("❌ Erro ao salvar a lista de usuários.")


@router.message(Command("list_users"))
async def cmd_list_users(message: types.Message):
    """List all allowed users."""
    allowed_users = load_allowed_users()

    if not allowed_users:
        await message.reply("📋 Nenhum usuário permitido configurado.")
        return

    users_list = "\n".join([f"• @{user}" for user in sorted(allowed_users)])
    await message.reply(f"📋 <b>Usuários permitidos:</b>\n\n{users_list}", parse_mode="HTML")


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
        if command.args and command.args.strip():
            try:
                limit = int(command.args.strip())
            except ValueError:
                await message.reply("❌ Número inválido. Use: /tldr ou /tldr [número]")
                return

            if limit > 300:
                await message.reply("Tu ta muito engraçado, palhaço gozadola.. Gustavo tem fimose. Limite de 300")
                return
        else:
            limit = 100

        # Get message limit (default 100)
        limit = int(command.args) if command.args and command.args.isdigit() else 100
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
        prompt = f"Faça um resumo conciso das principais discussões desta conversa em português:\n\n{conversation} Retorne sem tags HTML."
        if LM_STUDIO_API.is_avaiable():
            summary = LM_STUDIO_API.chat(prompt)
        else:
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

    except Exception as e:
        logging.error(f"Error generating TLDR: {e}")
        # Try to edit if processing_message exists, otherwise reply to original
        try:
            await processing_message.edit_text("❌ Erro ao gerar resumo.")
        except:
            await message.reply("❌ Erro ao gerar resumo.")


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
        'oldest_message': None,
        'user_counts': {},
        'user_characters': {}
    }

    for msg in reversed(messages):  # most recent first
        # Handle potential database schema variations
        if len(msg) < 8:
            stats['media_ignored'] += 1
            continue

        # Database schema: id, user, message_id, text, replied_to, from_bot, kind, created
        # Skip the id field and unpack the rest
        _, user, message_id, text, replied_to, from_bot, kind, created = msg

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

        # Count messages by user
        if user in stats['user_counts']:
            stats['user_counts'][user] += 1
        else:
            stats['user_counts'][user] = 1

        # Count characters by user
        if user in stats['user_characters']:
            stats['user_characters'][user] += len(text)
        else:
            stats['user_characters'][user] = len(text)

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

    stats_text = "\n\n📊 <b>Estatísticas:</b>\n"
    stats_text += f"• {stats['total_messages']} mensagens analisadas\n"
    stats_text += f"• {total_ignored} ignoradas ({stats['media_ignored']} mídias, {stats['bots_ignored']} bots, etc.)\n"

    # Add user statistics (messages and characters)
    if stats['user_counts']:
        # Find who talked the most (by characters)
        if stats['user_characters']:
            most_talkative_user = max(stats['user_characters'].items(), key=lambda x: x[1])
            user_name, char_count = most_talkative_user

            # Special message for Wdiegon
            if user_name.lower() == "wdiegon":
                stats_text += f"• Quem falou mais: {user_name}, rei do lero lero\n"
            else:
                stats_text += f"• Quem falou mais: {user_name}\n"

        stats_text += "• Atividade por usuário:\n"
        # Sort users by message count (descending)
        sorted_users = sorted(stats['user_counts'].items(), key=lambda x: x[1], reverse=True)
        for user, msg_count in sorted_users[:5]:  # Show top 5 users
            char_count = stats['user_characters'].get(user, 0)
            stats_text += f"  - {user}: {msg_count} msgs, {char_count} chars\n"
        if len(sorted_users) > 5:
            stats_text += f"  - E mais {len(sorted_users) - 5} usuários...\n"

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


@router.message(F.text.contains('@') | F.caption.contains('@'))
async def mention_handler(message: types.Message):
    # Only respond to allowed users
    bot_username = (await message.bot.get_me()).username

    # Get text from either text or caption (for media messages)
    message_text = message.text or message.caption or ""

    # Check if bot is mentioned and user is allowed
    if f"@{bot_username}" not in message_text:
        return

    # Check if user is allowed
    if not is_user_allowed(message.from_user.username):
        return

    try:
        # Extract the question (remove bot mention)
        question = message_text.replace(f"@{bot_username}", "").strip()

        # Check for images and prepare context
        image_url = None
        context_parts = []

        # Check if this is a reply to another message
        if message.reply_to_message:
            replied_msg = message.reply_to_message
            original_user = replied_msg.from_user.username if replied_msg.from_user else "Unknown"
            original_text = replied_msg.text or "[mídia/sem texto]"

            context_parts.append(f"Contexto: {original_user} disse: '{original_text}'")
            context_parts.append(f"Pergunta de {message.from_user.username}: {question}")

            # Check for image in the replied message
            if replied_msg.photo:
                # Get the largest photo
                photo = replied_msg.photo[-1]
                file = await message.bot.get_file(photo.file_id)
                image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"
            elif replied_msg.document and replied_msg.document.mime_type and replied_msg.document.mime_type.startswith('image/'):
                file = await message.bot.get_file(replied_msg.document.file_id)
                image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"
        else:
            context_parts.append(f"Pergunta de {message.from_user.username}: {question}")

            # Check for image in the current message
            if message.photo:
                photo = message.photo[-1]
                file = await message.bot.get_file(photo.file_id)
                image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"
            elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'):
                file = await message.bot.get_file(message.document.file_id)
                image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"

        # Build the final prompt
        prompt = "\n".join(context_parts) if context_parts else question

        # Call Z_AI with or without image
        response = Z_AI_API.chat(prompt, image_url=image_url)

        logging.info(f"Mention response: {response}")
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
    global consecutive_messages, last_user

    current_user = message.from_user.username if message.from_user else message.from_user.id

    # Reset counter if different user
    if last_user != current_user:
        consecutive_messages = {}
        last_user = current_user

    # Increment counter for current user
    consecutive_messages[current_user] = consecutive_messages.get(current_user, 0) + 1

    # Check if user exceeded 6 consecutive messages
    if consecutive_messages[current_user] > 6:
        consecutive_messages[current_user] = 0
        await message.reply_photo("https://pbs.twimg.com/media/EmUwc6jU0AEq4DB.jpg")

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
