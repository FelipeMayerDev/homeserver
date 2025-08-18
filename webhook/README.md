# Webhook Service

This is a minimal FastAPI webhook service that can receive and process incoming webhooks.

## Features

- Basic webhook endpoint at `/webhook`
- Health check endpoint at `/health`
- Root endpoint at `/` for service verification
- Docker support
- Environment variable configuration

## Setup

1. Copy the `.env.sample` file to `.env` and modify as needed:
   ```bash
   cp .env.sample .env
   ```

2. Build and run the service using Docker:
   ```bash
   docker-compose up --build
   ```

## Endpoints

- `GET /` - Service root, confirms the service is running
- `GET /health` - Health check endpoint
- `POST /webhook` - Main webhook endpoint that processes incoming requests

## Configuration

The service can be configured using environment variables in the `.env` file:

- `PORT` - The port the service runs on (default: 8000)

## Development

To run the service locally for development:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the service:
   ```bash
   python main.py
   ```

The service will be available at `http://localhost:8000`.