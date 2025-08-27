import requests
import re
import json
import os
from shared.database import History
import logging

# File to store message IDs
MESSAGE_IDS_FILE = "message_ids.json"
# Key for the single message (independent of channel)
SINGLE_MESSAGE_KEY = "single_event_message"

def load_message_ids():
    """Load message IDs from file"""
    if os.path.exists(MESSAGE_IDS_FILE):
        with open(MESSAGE_IDS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_message_ids(message_ids):
    """Save message IDs to file"""
    with open(MESSAGE_IDS_FILE, 'w') as f:
        json.dump(message_ids, f)

def get_last_discord_event_message():
    """Get the last discord_event message from the database"""
    try:
        history = History()
        # Get last 5 messages
        messages = history.get_all_messages(5)
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
        event_key (str): Event key (not used in this implementation to keep it channel-independent)
        kind (str): Message kind to determine if we should edit or send new
    
    Returns:
        dict: Response from Telegram API
    """
    # If kind is "discord_event", try to edit the last discord_event message
    if kind == "discord_event":
        last_message_id = get_last_discord_event_message()
        logging.info(f"Last discord_event message ID: {last_message_id}")
        if last_message_id:
            # Try to edit the last discord_event message
            url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
            payload = {
                "chat_id": chat_id,
                "message_id": last_message_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=payload)
            
            # If editing fails because message not found, send a new one
            if response.status_code != 200:
                result = response.json()
                if "error_code" in result and result["error_code"] == 400:
                    # Message not found, send new one
                    return send_new_message(bot_token, chat_id, message, SINGLE_MESSAGE_KEY, load_message_ids())
            return response.json()
    
    # For non-discord_event messages or if no previous discord_event message found,
    # use the existing logic
    message_ids = load_message_ids()
    
    # Always use the same key for all events
    message_key = SINGLE_MESSAGE_KEY
    
    # Try to edit existing message first
    if message_key in message_ids:
        message_id = message_ids[message_key]
        url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload)
        
        # If editing fails because message not found, send a new one
        if response.status_code != 200:
            result = response.json()
            if "error_code" in result and result["error_code"] == 400:
                # Message not found, send new one
                return send_new_message(bot_token, chat_id, message, message_key, message_ids)
        return response.json()
    else:
        # Send new message
        return send_new_message(bot_token, chat_id, message, message_key, message_ids)

def send_new_message(bot_token, chat_id, message, message_key, message_ids):
    """Send a new message and store its ID"""
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
            # Store message ID for future editing
            message_ids[message_key] = result["result"]["message_id"]
            save_message_ids(message_ids)
    
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

def send_or_edit_telegram_image(bot_token, chat_id, image, caption=None, message_key="single_image_message"):
    """
    Send a new image message or edit the existing one
    
    Args:
        bot_token (str): Telegram bot token
        chat_id (str): Telegram chat ID
        image (str): URL or file path of the image
        caption (str, optional): Caption text for the image
        message_key (str): Key to identify the message for editing
    
    Returns:
        dict: Response from Telegram API
    """
    message_ids = load_message_ids()
    
    # Try to edit existing message first
    if message_key in message_ids:
        message_id = message_ids[message_key]
        url = f"https://api.telegram.org/bot{bot_token}/editMessageCaption"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "caption": caption or "",
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload)
        
        # If editing fails because message not found, send a new one
        if response.status_code != 200:
            result = response.json()
            if "error_code" in result and result["error_code"] == 400:
                # Message not found, send new one
                return send_new_image_message(bot_token, chat_id, image, caption, message_key, message_ids)
        return response.json()
    else:
        # Send new message
        return send_new_image_message(bot_token, chat_id, image, caption, message_key, message_ids)

def send_new_image_message(bot_token, chat_id, image, caption, message_key, message_ids):
    """Send a new image message and store its ID"""
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
        
    if response.status_code == 200:
        result = response.json()
        if "result" in result and "message_id" in result["result"]:
            # Store message ID for future editing
            message_ids[message_key] = result["result"]["message_id"]
            save_message_ids(message_ids)
    
    return response.json()
