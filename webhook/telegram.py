import requests
import re
import json
import os
import time

# File to store message IDs and timestamps
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

def escape_markdown(text):
    """
    Escape special characters for Telegram Markdown v2
    """
    # Characters that need to be escaped in Markdown v2: _ * [ ] ( ) ~ ` > # + - = | { } . !
    escape_chars = r'_[]()~`>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\\1', text)

def should_edit_message(bot_token, chat_id, message_data):
    """
    Determine if we should edit the existing message or send a new one.
    We should only edit if:
    1. The message exists
    2. Less than 5 minutes have passed since the last edit/send
    
    Args:
        bot_token (str): Telegram bot token
        chat_id (str): Telegram chat ID
        message_data (dict): Stored message data including message_id and timestamp
        
    Returns:
        bool: True if we should edit the message, False if we should send a new one
    """
    if not message_data:
        return False
    
    # Check if less than 5 minutes have passed
    current_time = time.time()
    if current_time - message_data.get("timestamp", 0) > 300:  # 5 minutes
        return False
    
    # If we passed the time check, we'll try to edit
    return True

def send_or_edit_telegram_message(bot_token, chat_id, message, event_key=None):
    """
    Send a new message or edit the existing one (independent of channel)
    Only edits the message if it was recently sent by the bot and is among the last
    few messages in the chat to avoid flood issues.
    
    Args:
        bot_token (str): Telegram bot token
        chat_id (str): Telegram chat ID
        message (str): Message text
        event_key (str): Event key (not used in this implementation to keep it channel-independent)
    
    Returns:
        dict: Response from Telegram API
    """
    message_ids = load_message_ids()
    
    # Always use the same key for all events
    message_key = SINGLE_MESSAGE_KEY
    
    # Check if we should edit the existing message
    if message_key in message_ids and should_edit_message(bot_token, chat_id, message_ids[message_key]):
        message_id = message_ids[message_key]["message_id"]
        url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload)
        
        result = response.json()
        # If editing succeeds, update the timestamp
        if response.status_code == 200:
            # Update timestamp
            message_ids[message_key]["timestamp"] = time.time()
            save_message_ids(message_ids)
            return result
        elif response.status_code != 200 and "error_code" in result:
            # If editing fails due to message not found, send a new message
            if result["error_code"] == 400:
                return send_new_message(bot_token, chat_id, message, message_key, message_ids)
        return result
    else:
        # Send new message
        return send_new_message(bot_token, chat_id, message, message_key, message_ids)

def send_new_message(bot_token, chat_id, message, message_key, message_ids):
    """Send a new message and store its ID and timestamp"""
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
            # Store message ID and timestamp for future editing
            message_ids[message_key] = {
                "message_id": result["result"]["message_id"],
                "timestamp": time.time()
            }
            save_message_ids(message_ids)
    
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
