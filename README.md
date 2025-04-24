# Discord Ollama Chatbot

This project is a Discord bot that uses Ollama for AI chat responses, accessible via a `/chat` slash command. The entire stack runs in Docker using `docker-compose`.

## Features
- Discord bot with `/chat` command
- Connects to Ollama for AI-generated responses
- Easy deployment with Docker Compose

## Setup

1. **Clone the repository**
2. **Create a `.env` file** in the project root:
   ```
   DISCORD_TOKEN=your_discord_token_here
   ```
3. **Build and start the services:**
   ```sh
   docker-compose up --build
   ```
4. **Invite your bot to your Discord server** (if not already done)
5. **Use `/chat` in your server to interact with Ollama**

## Notes
- Your `.env` file is excluded from version control for security.
- Ollama runs as a service and is accessible to the bot at `http://ollama:11434`.

## Requirements
- Docker & Docker Compose
- Discord bot token (see Discord Developer Portal)

## License
MIT
