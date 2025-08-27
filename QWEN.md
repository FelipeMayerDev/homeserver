# HomeServer Project

This is a personal home server setup hosting various services for personal use.

## Services Overview

### 1. Discord Bot - Music Player
- Plays music in Discord voice channels
- Queue management and volume control
- Skip, pause, and resume functionality
- Voice channel join/leave notifications

### 2. Telegram Bot
- Stores all sent and received messages in SQLite database (messages.db)
- Database schema includes user, message_id, text, replied_to, from_bot, and created timestamp
- Database file is git-ignored for privacy protection

### 3. Webhook Service
- FastAPI webhook service for receiving and processing external webhooks
- Features:
  - Webhook endpoint at `/webhook`
  - Health check at `/health`
  - Docker support
  - Environment variable configuration

### 4. Steam Profile Monitor
- Monitors Steam profiles for game activity
- Sends webhook notifications when users start playing games
- Configurable cooldown time between checks
- Uses cookies and realistic headers to avoid detection

## Technical Details

- **Orchestration**: Docker Compose (compose.yml)
- **Services**: 4 containers (discord-bot, telegram-bot, webhook, steam)
- **Shared Resources**: All services mount the `shared` directory
- **Environment**: Each service uses its own .env file
- **Persistence**: Telegram bot stores messages in SQLite database

## Setup

1. Clone repository
2. Configure environment variables for each service
3. For Steam service, create `cookies.txt` in steam directory
4. Run with `docker-compose up -d`

## Notes

- This is a personal project with no formal testing
- Performance-focused implementation
- Privacy-conscious design (database files are git-ignored)