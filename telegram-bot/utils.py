import os
from aiogram import types, Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import LinkPreviewOptions
from ai_tools import GROQ_API, GOOGLE_IMAGE_API
from yt_dlp import YoutubeDL
import logging

async def transcribe_media(message: types.Message, bot: Bot, media_type: str, file_id: str, file_extension: str):
    """
    Generic function to handle media transcription
    
    Args:
        message: The Telegram message object
        bot: The Telegram bot instance
        media_type: Type of media (voice, video, audio, video_note)
        file_id: Telegram file ID
        file_extension: File extension for saving
    """
    # Define messages based on media type
    messages = {
        "video": ("Processando seu vídeo...", "📺 <b>Transcrição do vídeo:</b>\n\n{}"),
        "video_note": ("Processando sua nota de vídeo...", "📺 <b>Transcrição da nota de vídeo:</b>\n\n{}"),
        "audio": ("Processando seu áudio...", "🎵 <b>Transcrição do áudio:</b>\n\n{}"),
        "voice": ("Processando sua mensagem de voz...", "🎤 <b>Transcrição da mensagem de voz:</b>\n\n{}")
    }
    
    # Get appropriate messages
    processing_msg, response_template = messages.get(media_type, ("Processing...", "{}"))
    
    # Send processing message and keep a reference to it
    processing_message = await message.reply(processing_msg)
    
    # Download the media file
    file = await bot.get_file(file_id)
    file_path = file.file_path
    file_name = f"{media_type}_{message.message_id}.{file_extension}"
    
    await bot.download_file(file_path, file_name)
    logging.info(f"Downloaded {media_type} file: {file_name}")
    try:
        transcription = GROQ_API.transcribe_audio(file_name)

        await processing_message.edit_text(response_template.format(transcription))
    except Exception as e:
        # Define error messages based on media type
        error_messages = {
            "video": "❌ Não foi possível transcrever o áudio do vídeo.",
            "video_note": "❌ Não foi possível transcrever o áudio da nota de vídeo.",
            "audio": "❌ Não foi possível transcrever o áudio.",
            "voice": "❌ Não foi possível transcrever a mensagem de voz."
        }
        
        error_msg = error_messages.get(media_type, "❌ Não foi possível transcrever o arquivo.")
        await processing_message.edit_text(error_msg)
    finally:
        # Clean up the downloaded file
        if os.path.exists(file_name):
            os.remove(file_name)


async def send_image_with_button(message: types.Message, query: str):
    """
    Search for an image based on the query and send it to the user with a button to request another
    
    Args:
        message: The Telegram message object
        query: Str containing the command and query
    """
    searching_message = await message.answer(f"🔍 Procurando imagem de: {query}")
    try:
        image_url = GOOGLE_IMAGE_API.get_image(query)
        if image_url:
            # Create inline keyboard with "Pedir outra?" button
            builder = InlineKeyboardBuilder()
            builder.add(types.InlineKeyboardButton(
                text="Pedir outra?",
                callback_data=f"another_image:{query}"
            ))
            
            await message.reply_photo(
                image_url, 
                caption=f"🖼️ Aqui está uma imagem de: {query}",
                reply_markup=builder.as_markup()
            )
            await searching_message.delete()
        else:
            await searching_message.edit_text("❌ Não foi possível encontrar uma imagem para a sua consulta.")
    except Exception as e:
        await searching_message.edit_text("❌ Ocorreu um erro ao buscar a imagem.")


async def search_and_send_image(message: types.Message, query: str):
    """
    Search for an image based on the query and send it to the user
    
    Args:
        message: The Telegram message object
        query: Str containing the command and query
    """
    await send_image_with_button(message, query)

def is_valid_link(link: str) -> bool:
    """
    Check if the link is a valid YouTube or Facebook link
    """
    allowed_urls = [
        "https://x.com/",
        "https://www.instagram.com/reel/",
        "https://bsky.app/profile",
        "https://www.youtube.com/shorts/"
    ]
    for url in allowed_urls:
        if url in link:
            return True
    return False

async def send_media_stream(message: types.Message, force_download=False) -> dict:
    """
    Extrai a URL do vídeo de um link do YouTube ou de um vídeo do Facebook.
    """
    error_check = False
    download = True if force_download else False
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best[ext=mp4]',
        'postprocessor_args': [
            '-movflags', '+faststart',
        ],
        'get_url': True,
        "cookiefile": "cookies.txt"
    }
    if download:
        ydl_opts["format"] = 'best[filesize<50M][ext=mp4]/best[ext=mp4]'

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(message.text, download=download)

            if "instagram" in message.text:
                for f in info["formats"]:
                    if list(f.keys())[0] == "url":
                        custom_url = f["url"]

            if download:
                video_file = ydl.prepare_filename(info)
                with open(video_file, 'rb') as video:
                    await message.reply_video(
                        video=types.FSInputFile(video_file),
                        caption=f'***{info.get("title")}***',
                        parse_mode="Markdown"
                    )
                os.remove(video_file)
                return

            video_data = {
                "url": info.get('url'),
                "title": info.get('title'),
                "description": info.get('description')
            }
            await message.reply_video(
                video=video_data["url"], 
                caption=f'***{video_data["title"]}***', 
                parse_mode="Markdown"
            )

    except Exception as e:
        if error_check:
            await message.reply("❌ Ocorreu um erro ao processar o vídeo.")
        error_check = True
        await send_media_stream(message, force_download=True)