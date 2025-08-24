import requests
import re

def escape_markdown(text):
    """
    Escape special characters for Telegram Markdown v2
    """
    # Characters that need to be escaped in Markdown v2: _ * [ ] ( ) ~ ` > # + - = | { } . !
    escape_chars = r'_[]()~`>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\1', text)

def send_telegram_message(bot_token, chat_id, message):
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
