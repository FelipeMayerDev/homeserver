from fastapi import FastAPI, Request
import uvicorn
import os
from dotenv import load_dotenv
from telegram import send_telegram_message, escape_markdown, send_telegram_image, send_or_edit_telegram_message
from shared.ai_tools import GOOGLE_IMAGE_API
from shared.database import History
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

load_dotenv()

app = FastAPI(title="Webhook Service")

# Initialize the database
history = History()

@app.get("/")
async def root():
    return {"message": "Webhook service is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/messages")
async def save_message(request: Request):
    """Save a message to the database."""
    try:
        data = await request.json()
        user = data.get("user")
        message_id = data.get("message_id")
        text = data.get("text")
        replied_to = data.get("replied_to")
        from_bot = data.get("from_bot", False)
        kind = data.get("kind")
        
        # Save to database with kind
        message_id = history.save_message(user, message_id, text, replied_to, from_bot, kind)
        return {"status": "success", "message_id": message_id}
    except Exception as e:
        logging.error(f"Error saving message: {e}")
        return {"error": str(e)}

@app.get("/messages/{message_id}")
async def get_message(message_id: str):
    """Retrieve a message by its ID."""
    try:
        message = history.get_message(message_id)
        if message:
            return {"status": "success", "message": message}
        else:
            return {"status": "not_found"}
    except Exception as e:
        logging.error(f"Error retrieving message: {e}")
        return {"error": str(e)}

@app.get("/messages/user/{user}")
async def get_messages_by_user(user: str, limit: int = 100):
    """Retrieve messages sent by a specific user."""
    try:
        messages = history.get_messages_by_user(user, limit)
        return {"status": "success", "messages": messages}
    except Exception as e:
        logging.error(f"Error retrieving messages for user {user}: {e}")
        return {"error": str(e)}

@app.get("/messages")
async def get_all_messages(limit: int = 100):
    """Retrieve all messages, ordered by creation time."""
    try:
        messages = history.get_all_messages(limit)
        return {"status": "success", "messages": messages}
    except Exception as e:
        logging.error(f"Error retrieving all messages: {e}")
        return {"error": str(e)}

@app.post("/steam/profiles")
async def steam_profiles(request: Request):
    try:
        logging.info("Receiving data from Steam...")
        data = await request.json()
        user, game = data.get("profile"), data.get("game")
        message = f"🎮 {user} is now playing {game}"
        query_image = GOOGLE_IMAGE_API.get_image(f"Gameplay {game}")
        send_telegram_image(
            os.getenv("TELEGRAM_BOT_TOKEN"),
            os.getenv("TELEGRAM_CHAT_ID"),
            image=query_image,
            caption=message
        )
        history.save_message(
            user="steam_bot",
            from_bot=True,
            message_id=f"steam_event_{hash(message)}",  # Generate a unique ID
            text=message,
            kind="steam_event"
        )
    except Exception as e:
        print(f"Error receiving data: {e}")	

@app.post("/discord/voice_state")
async def discord_voice_state(request: Request):
    try:
        data = await request.json()

        channel = data.get("channel")
        users_in_channel = data.get("users_in_channel", [])
        events = data.get("events", [])

        if not channel:
            return {"status": "ignored"}

        # Mantém o último status de cada usuário
        last_status = {}
        for ev in events:
            parts = ev.split(" ", 1)
            if len(parts) == 2:
                user, action = parts
                last_status[user] = action.lower()  # sobrescreve sempre

        # Classifica por tipo de evento
        joined = [u for u, a in last_status.items() if "joined" in a]
        left = [u for u, a in last_status.items() if "left" in a]
        switched = [u for u, a in last_status.items() if "switched" in a]

        messages = []

        if joined:
            messages.append(f"🎙️ Entraram em *{escape_markdown(channel)}*: {', '.join(joined)}\n")
        if left:
            messages.append(f"🎙️ Saíram de *{escape_markdown(channel)}*: {', '.join(left)}\n")
        if switched:
            messages.append(f"🎙️ Mudaram de canal para *{escape_markdown(channel)}*: {', '.join(switched)}\n")

        # Só mostra membros se realmente tiver alguém na sala
        if users_in_channel:
            members_str = "\n".join([f"- {escape_markdown(u)}" for u in users_in_channel])
            messages.append(f"👥 Membros em *{escape_markdown(channel)}*:\n{members_str}")

        if messages:
            final_message = "\n".join(messages)
            logging.info(f"Enviando/atualizando mensagem para Telegram: {final_message}")
            # Use the new function that can edit existing messages
            telegram_response = send_or_edit_telegram_message(
                os.getenv("TELEGRAM_BOT_TOKEN"),
                os.getenv("TELEGRAM_CHAT_ID"),
                final_message,
                kind="discord_event"
            )
            
            if isinstance(telegram_response, dict):
                telegram_message_id = telegram_response["result"]["message_id"]
            else:
                telegram_message_id = telegram_response.json()["result"]["message_id"]
            
            history.save_message(
                user="discord_bot",
                from_bot=True,
                message_id=telegram_message_id,
                text=final_message,
                kind="discord_event"
            )

        return {"status": "ok"}

    except Exception as e:
        logging.info(type(telegram_response))
        print("Erro ao processar webhook:", telegram_response)
        return {"status": "error"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)