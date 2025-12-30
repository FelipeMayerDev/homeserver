import os
import uuid
import logging
from aiogram import types, Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import LinkPreviewOptions
from shared.ai_tools import GROQ_API, GOOGLE_IMAGE_API
from yt_dlp.utils import ExtractorError, DownloadError
from yt_dlp import YoutubeDL

class VideoNotFound(Exception):
    pass

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
        "https://www.instagram.com/p/",
        "https://bsky.app/profile",
        "https://www.youtube.com/shorts/",
        "https://www.facebook.com/watch?v="
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
        'format': 'best[height<=720][ext=mp4]/best[height<=720]/best[ext=mp4]/best',
        'postprocessor_args': [
            '-movflags', '+faststart',
        ],
        'get_url': True,
        'cookiefile': 'cookies.txt'
    }
    if download:
        ydl_opts["format"] = 'best[filesize<50M][height<=720][ext=mp4]/best[filesize<50M][ext=mp4]/best[height<=720][ext=mp4]/best[ext=mp4]/best'

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(message.text, download=download)
            if not info.get("url") and not info.get("formats"):
                resource_id = message.text.split("/")[-1]
                raise ExtractorError(
                    f"[{info.get('extractor', 'generic')}] {resource_id}: No video could be found",
                    expected=True
                )
            if "instagram" in message.text:
                for f in info["formats"]:
                    if list(f.keys())[0] == "url":
                        custom_url = f["url"]

            if download:
                video_file = ydl.prepare_filename(info)
                with open(video_file, 'rb') as video:
                    sender = message.from_user.username or message.from_user.id if message.from_user else "Unknown"
                    caption = f'***{info.get("title")}***\n\nLink: {message.text}\nEnviado por: {sender}'
                    await message.reply_video(
                        video=types.FSInputFile(video_file),
                        caption=caption,
                        parse_mode="Markdown"
                    )
                os.remove(video_file)
                return

            video_data = {
                "url": info.get('url'),
                "title": info.get('title'),
                "description": info.get('description')
            }
            sender = message.from_user.username or message.from_user.id if message.from_user else "Unknown"
            caption = f'***{video_data["title"]}***\n\nLink: {message.text}\nEnviado por: {sender}'
            await message.reply_video(
                video=video_data["url"],
                caption=caption,
                parse_mode="Markdown"
            )
    except ExtractorError as e:
        if "Requested format is not available" in str(e) or "format" in str(e).lower():
            # If the preferred format is not available, try with a more flexible format
            ydl_opts_alt = {
                'quiet': True,
                'no_warnings': True,
                'format': 'best[ext=mp4]/best[ext=webm]/best',
                'postprocessor_args': [
                    '-movflags', '+faststart',
                ],
                'get_url': True,
                'cookiefile': 'cookies.txt'
            }
            try:
                with YoutubeDL(ydl_opts_alt) as ydl:
                    info = ydl.extract_info(message.text, download=download)
                    if download:
                        video_file = ydl.prepare_filename(info)
                        with open(video_file, 'rb') as video:
                            sender = message.from_user.username or message.from_user.id if message.from_user else "Unknown"
                            caption = f'***{info.get("title")}***\n\nLink: {message.text}\nEnviado por: {sender}'
                            await message.reply_video(
                                video=types.FSInputFile(video_file),
                                caption=caption,
                                parse_mode="Markdown"
                            )
                        os.remove(video_file)
                        return

                    video_data = {
                        "url": info.get('url'),
                        "title": info.get('title'),
                        "description": info.get('description')
                    }
                    sender = message.from_user.username or message.from_user.id if message.from_user else "Unknown"
                    caption = f'***{video_data["title"]}***\n\nLink: {message.text}\nEnviado por: {sender}'
                    await message.reply_video(
                        video=video_data["url"],
                        caption=caption,
                        parse_mode="Markdown"
                    )
            except Exception as e_alt:
                raise VideoNotFound(f"❌ Ocorreu um erro ao processar o vídeo mesmo com formato alternativo. {e_alt}")
        else:
            raise VideoNotFound(f"❌ Ocorreu um erro ao processar o vídeo. {e}")
    except (ExtractorError, DownloadError) as e:
        raise VideoNotFound(f"❌ Ocorreu um erro ao processar o vídeo. {e}")

    except Exception as e:
        if error_check:
            await message.reply(f"❌ Ocorreu um erro ao processar o vídeo. {e}")
        error_check = True
        await send_media_stream(message, force_download=True)


async def process_youtube_video(youtube_url: str) -> str:
    """
    Download YouTube video audio, transcribe it, and generate a summary.

    Args:
        youtube_url: URL of the YouTube video

    Returns:
        Summary of the video content
    """
    from shared.ai_tools import GROQ_API
    import tempfile
    import uuid

    # Create a temporary file name
    temp_filename = f"temp_audio_{uuid.uuid4().hex}.mp3"

    try:
        # Download only the audio from YouTube video
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'postprocessor_args': [
                '-ar', '16000'
            ],
            'prefer_ffmpeg': True,
            'keepvideo': False,
            'outtmpl': temp_filename.replace('.mp3', ''),  # yt-dlp will add .mp3
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

        # Check if the file was created
        if not os.path.exists(temp_filename):
            raise Exception("Failed to download audio file")

        # Transcribe the audio
        transcription = GROQ_API.transcribe_audio(temp_filename)

        # Generate summary using GROQ API
        summary_prompt = "Você é uma ferramenta de resumir e summarizar conteúdos, retorne o resumo do que foi dito nesse video.. seja breve mas consiso. Responda apenas em texto.. NOT ALLOWED MARKDOWN AND HTML"
        summary = GROQ_API.chat(f"{summary_prompt}\n\n{transcription}")

        return summary

    except DownloadError as e:
        if "Requested format is not available" in str(e) or "format" in str(e).lower():
            # If the preferred format is not available, try with a more flexible format
            ydl_opts_alt = {
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'postprocessor_args': [
                    '-ar', '16000'
                ],
                'prefer_ffmpeg': True,
                'keepvideo': False,
                'outtmpl': temp_filename.replace('.mp3', ''),  # yt-dlp will add .mp3
            }

            with YoutubeDL(ydl_opts_alt) as ydl:
                ydl.download([youtube_url])

            # Check if the file was created
            if not os.path.exists(temp_filename):
                raise Exception("Failed to download audio file with alternative format")

            # Transcribe the audio
            transcription = GROQ_API.transcribe_audio(temp_filename)

            # Generate summary using GROQ API
            summary_prompt = "Você é uma ferramenta de resumir e summarizar conteúdos, retorne o resumo do que foi dito nesse video.. seja breve mas consiso. Responda apenas em texto.. NOT ALLOWED MARKDOWN AND HTML"
            summary = GROQ_API.chat(f"{summary_prompt}\n\n{transcription}")

            return summary
        else:
            raise e

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
