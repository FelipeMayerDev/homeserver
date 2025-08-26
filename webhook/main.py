from fastapi import FastAPI, Request
import uvicorn
import os
from dotenv import load_dotenv
from telegram import send_telegram_message, escape_markdown, send_telegram_image
from shared.ai_tools import GOOGLE_IMAGE_API
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

load_dotenv()

app = FastAPI(title="Webhook Service")

@app.get("/")
async def root():
    return {"message": "Webhook service is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/steam/profiles")
async def steam_profiles(request: Request):
    try:
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
            from telegram import send_or_edit_telegram_message
            send_or_edit_telegram_message(
                os.getenv("TELEGRAM_BOT_TOKEN"),
                os.getenv("TELEGRAM_CHAT_ID"),
                final_message
            )

        return {"status": "ok"}

    except Exception as e:
        print("Erro ao processar webhook:", e)
        return {"status": "error"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)