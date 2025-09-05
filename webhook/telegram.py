import requests
import re
import json
import os
from shared.database import History
import logging

# Key for the single message (independent of channel)
SINGLE_MESSAGE_KEY = "single_event_message"

def get_message_id_from_db(message_key):
    """Get message ID from database using the message key"""
    try:
        history = History()
        # We'll use a special user identifier for system messages
        # and store the message_key in the replied_to field
        messages = history.get_messages_by_user("discord_bot", 100)
        for message in messages:
            # message format: (id, user, message_id, text, replied_to, from_bot, kind, created)
            if message[4] == message_key and message[6] == "system_message":
                return message[2]  # Return message_id
        return None
    except Exception as e:
        logging.error(f"Error retrieving message ID from database: {e}")
        return None

def save_message_id_to_db(user, message_id, text, replied_to=None, from_bot=None, kind=None):
    """Save message ID to database with the message key"""
    try:
        history = History()
        # We'll use a special user identifier for system messages
        # and store the message_key in the replied_to field
        history.save_message(
            user=user,
            message_id=message_id,
            text=text,
            replied_to=replied_to,
            from_bot=from_bot,
            kind=kind
        )
    except Exception as e:
        logging.error(f"Error saving message ID to database: {e}")

def get_last_discord_event_message():
    """Get the last discord_event message from the database"""
    try:
        history = History()
        # Get last 5 messages
        messages = history.get_all_messages(1)
        # Look for a message with kind="discord_event"
        for message in messages:
            # message format: (id, user, message_id, text, replied_to, from_bot, kind, created)
            if message[6] == "discord_event":
                return message[2]  # Return message_id
        return None
    except Exception as e:
        print(f"Error retrieving last discord_event message: {e}")
        return None

def escape_markdown(text):
    """
    Escape special characters for Telegram Markdown v2
    """
    # Characters that need to be escaped in Markdown v2: _ * [ ] ( ) ~ ` > # + - = | { } . !
    escape_chars = r'_[]()~`>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\1', text)

def send_or_edit_telegram_message(bot_token, chat_id, message, event_key=None, kind=None):
    """
    Send a new message or edit the existing one (independent of channel)
    
    Args:
        bot_token (str): Telegram bot token
        chat_id (str): Telegram chat ID
        message (str): Message text
        event_key (str): Event key for identifying which message to edit
        kind (str): Message kind to determine if we should edit or send new
    
    Returns:
        dict: Response from Telegram API
    """
    # If kind is "discord_event", try to edit the last discord_event message
    if kind == "discord_event":
        last_message_id = get_last_discord_event_message()
        logging.info(f"Last discord_event message ID: {last_message_id}")
        if last_message_id:
            logging.info(f"Editing message ID: {last_message_id}")
            url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
            payload = {
                "chat_id": chat_id,
                "message_id": last_message_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            return requests.post(url, json=payload)
    
    logging.info(f"Sending new message: {message}")
    return send_new_message(bot_token, chat_id, message, event_key or SINGLE_MESSAGE_KEY)

def send_new_message(bot_token, chat_id, message, message_key):
    """Send a new message and store its ID in the database"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        if "result" in result and "message_id" in result["result"]:
            # Store message ID for future editing in the database
            save_message_id_to_db(
                user="discord_bot",
                message_id=result["result"]["message_id"],
                text=message,
                replied_to=message_key,
                from_bot=True,
                kind="discord_event"
            )
    
    return response.json()

def send_telegram_image(bot_token, chat_id, image, caption=None):
    """
    Send an image to Telegram chat with optional caption
    
    Args:
        bot_token (str): Telegram bot token
        chat_id (str): Telegram chat ID
        image (str): URL or file path of the image
        caption (str, optional): Caption text for the image
    
    Returns:
        dict: Response from Telegram API
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    payload = {
        "chat_id": chat_id
    }
    if caption:
        payload["caption"] = caption
        payload["parse_mode"] = "Markdown"
    
    files = None
    if image.startswith(('http://', 'https://')):
        payload["photo"] = image
        response = requests.post(url, json=payload)
    else:
        files = {
            "photo": open(image, 'rb')
        }
        response = requests.post(url, data=payload, files=files)
    
    if files and 'photo' in files:
        files['photo'].close()
        
    return response.json()

def send_telegram_message(bot_token, chat_id, message):
    """
    Legacy function for backward compatibility
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    return response.json()

