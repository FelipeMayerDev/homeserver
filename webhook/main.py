from fastapi import FastAPI, Request
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Webhook Service")

@app.get("/")
async def root():
    return {"message": "Webhook service is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    headers = dict(request.headers)
    
    print(f"Received webhook: {body.decode()}")
    print(f"Headers: {headers}")
    
    # Parse the JSON data
    try:
        data = await request.json()
        if data.get("event") == "joined":
            user = data.get("user")
            channel = data.get("channel")
            users_in_channel = data.get("users_in_channel", [])
            print(f"{user} joined in {channel}")
            print(f"Users in this channel: {', '.join(users_in_channel) if users_in_channel else 'No other users'}")
    except Exception as e:
        print(f"Error parsing JSON: {e}")
    
    return {"status": "received", "message": "Webhook processed successfully"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)