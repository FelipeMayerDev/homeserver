import os
from aiogram import types, Bot
from ai_tools import GROQ_API, GOOGLE_IMAGE_API


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
        "video": ("📥 Processando seu vídeo...", "📺 Transcrição do vídeo:\n\n{}"),
        "video_note": ("📥 Processando sua nota de vídeo...", "📺 Transcrição da nota de vídeo:\n\n{}"),
        "audio": ("📥 Processando seu áudio...", "🎵 Transcrição do áudio:\n\n{}"),
        "voice": ("📥 Processando sua mensagem de voz...", "🎤 Transcrição da mensagem de voz:\n\n{}")
    }
    
    # Get appropriate messages
    processing_msg, response_template = messages.get(media_type, ("Processing...", "{}"))
    
    # Send processing message
    await message.answer(processing_msg)
    
    # Download the media file
    file = await bot.get_file(file_id)
    file_path = file.file_path
    file_name = f"{media_type}_{message.message_id}.{file_extension}"
    
    await bot.download_file(file_path, file_name)
    
    try:
        # Transcribe the media
        transcription = GROQ_API.transcribe_audio(file_name)
        await message.answer(response_template.format(transcription))
    except Exception as e:
        # Define error messages based on media type
        error_messages = {
            "video": "❌ Não foi possível transcrever o áudio do vídeo.",
            "video_note": "❌ Não foi possível transcrever o áudio da nota de vídeo.",
            "audio": "❌ Não foi possível transcrever o áudio.",
            "voice": "❌ Não foi possível transcrever a mensagem de voz."
        }
        
        error_msg = error_messages.get(media_type, "❌ Não foi possível transcrever o arquivo.")
        await message.answer(error_msg)
    finally:
        # Clean up the downloaded file
        if os.path.exists(file_name):
            os.remove(file_name)


async def search_and_send_image(message: types.Message, command_parts: list):
    """
    Search for an image based on the query and send it to the user
    
    Args:
        message: The Telegram message object
        command_parts: List containing the command and query
    """
    query = message.text.split(" ", 1)
    if not query:
        return
    
    await message.answer(f"🔍 Procurando imagem de: {query}")
    
    try:
        image_url = GOOGLE_IMAGE_API.get_image(query)
        if image_url:
            await message.answer_photo(image_url, caption=f"🖼️ Aqui está uma imagem de: {query}")
        else:
            await message.answer("❌ Não foi possível encontrar uma imagem para a sua consulta.")
    except Exception as e:
        await message.answer("❌ Ocorreu um erro ao buscar a imagem.")