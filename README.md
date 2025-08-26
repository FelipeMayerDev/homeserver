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
4. For the Steam service, create a `cookies.txt` file in the steam directory with your session cookies in Netscape HTTP Cookie File format (you can export this from your browser)
5. Run the services with `python main.py` in each service directory

## Docker

This project includes a Docker setup for easy deployment:

```bash
docker-compose up -d
```

The webhook service will be available at `http://localhost:8000`.

## Contributing

This is a personal project, but suggestions and improvements are welcome.