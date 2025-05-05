# Discord Ollama Chatbot

This project is a Discord bot that uses Ollama for AI chat responses, accessible via a `/chat` slash command. The entire stack runs in Docker using `docker-compose`.

## Features
- Discord bot with `/chat` command (AI chat via Ollama)
- Summarization commands: `/tldr`, `/summarize`, ELI5 context menu
- Channel personality: `/setpersonality` and `!setpersonality` (admin only)
- **Sports commands:**
  - `/nba`, `/mlb`, `/nfl`, `/f1`, `/nascar`, `/pga` — live scores, next events, and recent results
  - `/nascar_winner`, `/f1_winner`, `/f1_winners` — recent race winners (dev only)
- **Finance:** `/btc` for Bitcoin price, `$TICKER` in chat for stock prices
- **Recommendations:** `/reccomendations`, `/addrec`, `/watched` — group TV show tracking
- **Reactions-based stats:** `/funniest`, `/stingy`, `/agreeable`, `/disagreeable` — leaderboards based on emoji reactions
- **Historian:** `/history`, `/import_history`, `/search`, `/message_count`, `Quote to Hall of Fame` context menu, `/quote`
- **Developer:** `/db_size` (dev only)
- Persistent SQLite database for all data (messages, recommendations, quotes, etc.)
- Easy deployment with Docker Compose

## Setup

1. **Clone the repository**
2. **Create a `.env` file** in the project root:
   ```
   DISCORD_TOKEN=your_discord_token_here
   # Optionally add OWNER_USER_ID, FINNHUB_API_KEY, etc.
   ```
3. **Build and start the services:**
   ```sh
   docker-compose up --build
   ```
4. **Invite your bot to your Discord server** (if not already done)
5. **Use `/chat` and other slash commands in your server**

## Notes
- Your `.env` file is excluded from version control for security.
- Ollama runs as a service and is accessible to the bot at `http://ollama:11434`.
- The bot uses a persistent SQLite database in `data/history.db`.
- Some commands (like `/setpersonality`, `/db_size`, `/nascar_winner`, `/f1_winner`, `/f1_winners`) are restricted to admins or development servers.
- For stock prices, set `FINNHUB_API_KEY` in your `.env`.

## Requirements
- Docker & Docker Compose
- Discord bot token (see Discord Developer Portal)
- (Optional) Finnhub API key for stock prices

## License
MIT
