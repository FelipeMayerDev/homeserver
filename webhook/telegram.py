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