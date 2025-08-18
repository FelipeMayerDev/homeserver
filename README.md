# HomeServer

This project is my personal home server setup that hosts various services for personal use.

## Services

### Discord Bot - Music Player

The first service hosted on this server is a Discord bot that can play music in voice channels. 

Features:
- Play songs from various sources
- Queue management
- Skip, pause, and resume functionality
- Voice channel join/leave notifications
- Slash commands for easy interaction

### Webhook Service

A minimal FastAPI webhook service that can receive and process incoming webhooks from external services.

Features:
- Basic webhook endpoint at `/webhook`
- Health check endpoint at `/health`
- Docker support
- Environment variable configuration

## Setup

To get started with this project, you'll need to:

1. Clone the repository
2. Configure the necessary environment variables for each service
3. Install dependencies with `npm install` in the discord-bot directory
4. Register slash commands with `node deploy-commands.js` in the discord-bot directory
5. Run the services with `npm start` in each service directory

## Docker

This project includes a Docker setup for easy deployment:

```bash
docker-compose up -d
```

The webhook service will be available at `http://localhost:8000`.

Note: After the first run, you may need to register the Discord bot slash commands by running:
```bash
docker exec -it discord-bot node deploy-commands.js
```

## Contributing

This is a personal project, but suggestions and improvements are welcome.