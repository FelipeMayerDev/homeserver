# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a containerized home server project hosting 4 interconnected services that communicate via HTTP webhooks and share a common SQLite database for message history tracking.

### Service Architecture
- **Discord Bot**: Music player bot with voice channel monitoring that sends webhook notifications
- **Telegram Bot**: Multi-feature bot with AI integration, media transcription, and message history logging
- **Webhook Service**: FastAPI-based central hub that receives webhooks from other services and manages Telegram notifications
- **Steam Monitor**: Scrapes Steam profiles for game activity and triggers webhook notifications

### Shared Components
- **Database Layer**: SQLite database (`shared/messages.db`) for cross-service message history
- **AI Tools**: Shared Groq API for chat completions, transcription, and vision; Google Search API for images
- **Inter-service Communication**: HTTP webhooks between services (Discord → Webhook, Steam → Webhook)

## Development Commands

### Docker Development
```bash
# Start all services
docker-compose up -d

# View logs for specific service
docker-compose logs -f discord-bot
docker-compose logs -f telegram-bot
docker-compose logs -f webhook
docker-compose logs -f steam

# Rebuild specific service
docker-compose build discord-bot
docker-compose up -d discord-bot

# Stop all services
docker-compose down
```

### Local Development
Each service can be run independently for development:
```bash
# Discord Bot
cd discord-bot
pip install -r requirements.txt
python main.py

# Telegram Bot
cd telegram_bot
pip install -r requirements.txt
python main.py

# Webhook Service
cd webhook
pip install -r requirements.txt
python main.py

# Steam Monitor
cd steam
pip install -r requirements.txt
python main.py
```

## Service Communication Flow

1. **Discord Bot** → **Webhook Service**: Voice state changes sent to `/discord/voice_state`
2. **Steam Monitor** → **Webhook Service**: Game activity sent to `/steam/profiles`
3. **Webhook Service** → **Telegram**: Formatted notifications sent via Telegram API
4. **All Services** → **Shared Database**: Message history stored in `shared/messages.db`

## Key Configuration

### Environment Variables
Each service requires its own `.env` file:
- `discord-bot/.env`: `DISCORD_TOKEN`
- `telegram_bot/.env`: `TELEGRAM_BOT_TOKEN`, `GROQ_API_KEY`, `SERPAPI_API_KEY`
- `webhook/.env`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `steam/.env`: `PROFILES`, `COOLDOWN_TIME`

### Steam Service Setup
Requires `cookies.txt` in Netscape HTTP Cookie File format for Steam authentication.

## Database Schema

The shared `messages` table schema:
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT NOT NULL,
    message_id TEXT NOT NULL,
    text TEXT NOT NULL,
    replied_to TEXT,
    from_bot BOOLEAN NOT NULL DEFAULT 0,
    kind TEXT,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Development Notes

- All services mount `./shared` directory for database access
- Webhook service exposes port 8000 for external webhooks
- Discord bot uses FFmpeg for audio processing (installed in Docker image)
- Telegram bot supports media transcription, image generation, and YouTube video summaries
- Steam monitor implements realistic headers and cookies to avoid detection