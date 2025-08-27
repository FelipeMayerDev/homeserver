# HomeServer

This project is my personal home server setup that hosts various services for personal use.

## Services

### Discord Bot - Music Player

The first service hosted on this server is a Discord bot that can play music in voice channels. 

Features:
- Play songs from various sources
- Queue management
- Volume control
- Skip, pause, and resume functionality
- Voice channel join/leave notifications

### Message History

The Telegram bot now stores all messages (both sent and received) in a SQLite database for auditing and analysis purposes. The database schema includes:
- `id`: Auto-incrementing primary key
- `user`: The user who sent the message (or the bot)
- `message_id`: The Telegram message ID
- `text`: The content of the message
- `replied_to`: The message ID this message is replying to (if any)
- `from_bot`: Boolean indicating if the message was sent by the bot
- `created`: Timestamp of when the message was created

This data is stored in a file named `messages.db` in the root directory, making it accessible to all services. Note that this file is intentionally ignored by Git to protect privacy and prevent accidental data leaks.

### Webhook Service

A minimal FastAPI webhook service that can receive and process incoming webhooks from external services.

Features:
- Basic webhook endpoint at `/webhook`
- Health check endpoint at `/health`
- Docker support
- Environment variable configuration

### Steam Profile Monitor

A service that monitors Steam profiles for game activity and sends notifications via webhooks.

Features:
- Monitor multiple Steam profiles for game activity
- Send webhook notifications when users start playing games
- Configurable cooldown time between checks
- Support for cookies and realistic headers to avoid detection

## Setup

To get started with this project, you'll need to:

1. Clone the repository
2. Configure the necessary environment variables for each service
3. Install dependencies with `pip install -r requirements.txt` in each service directory
4. For the Steam service:
   - Create a `cookies.txt` file in the steam directory with your session cookies in Netscape HTTP Cookie File format
   - You can export this from your browser using extensions like "Export Cookies" or "Cookie-Editor"
   - Make sure to export only the cookies for the steamcommunity.com domain
5. Run the services with `python main.py` in each service directory

## Docker

This project includes a Docker setup for easy deployment:

```bash
docker-compose up -d
```

The webhook service will be available at `http://localhost:8000`.

## Contributing

This is a personal project, but suggestions and improvements are welcome.