from fastapi import FastAPI, Request
import uvicorn
import os
from dotenv import load_dotenv
from telegram import send_telegram_message, escape_markdown

load_dotenv()

app = FastAPI(title="Webhook Service")

@app.get("/")
async def root():
    return {"message": "Webhook service is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/discord/voice_state")
async def discord_voice_state(request: Request):
    try:
        data = await request.json()
        user = data.get("user")
        channel = data.get("channel")
        users_in_channel = data.get("users_in_channel", [])
        event = data.get("event")

        # Escape user and channel names for Markdown
        user_name = escape_markdown(user[0])
        user_id = escape_markdown(user[1])
        channel_name = escape_markdown(channel)

        # Create members list with escaped names
        members_list = "".join(
            f"- {escape_markdown(membro[0])} ({escape_markdown(membro[1])})\n"
            for membro in users_in_channel
        )

        if event == "joined":
            message = (
                f"🎙️ *{user_name}* (__{user_id}__) entrou em *{channel_name}*"
            )
        elif event == "left":
            message = (
                f"🎙️ *{user_name}* (__{user_id}__) saiu de *{channel_name}*"
            )
        elif event == "switched":
            message = (
                f"🎙️ *{user_name}* (__{user_id}__) mudou de canal para *{channel_name}*"
            )

        if members_list:
            message += f"\n\n*👥 Membros no canal:*\n{members_list}"

        send_telegram_message(
            os.getenv("TELEGRAM_BOT_TOKEN"),
            os.getenv("TELEGRAM_CHAT_ID"),
            message
        )
            
    except Exception as e:
        print(f"Error processing webhook: {e}")
    
    return {"status": "received", "message": "Webhook processed successfully"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)