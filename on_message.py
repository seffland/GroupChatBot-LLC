import os
import requests
from ollama_client import ask_ollama
from db import add_message, get_history

def setup_on_message(bot, DEVELOPMENT_SERVER_ID, HISTORY_LIMIT):
    @bot.event
    async def on_message(message):
        if message.author.bot:
            return
        # DEV server only: Listen for $TICKER in messages and reply with stock price
        if message.guild and str(message.guild.id) == str(DEVELOPMENT_SERVER_ID):
            import re
            match = re.search(r'\$(\w{1,5})', message.content)
            if match:
                ticker = match.group(1).upper()
                try:
                    finnhub_api_key = os.getenv('FINNHUB_API_KEY')
                    if not finnhub_api_key:
                        await message.channel.send("Finnhub API key not set.")
                        return
                    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={finnhub_api_key}"
                    resp = requests.get(url, timeout=10)
                    data = resp.json()
                    if 'c' in data and data['c']:
                        price = data['c']
                        await message.channel.send(f"${ticker}: ${price}")
                    else:
                        await message.channel.send(f"Could not fetch price for ${ticker}.")
                except Exception as e:
                    await message.channel.send(f"Error fetching price for ${ticker}: {e}")
        # If the bot is mentioned, treat as a chat request
        if bot.user in message.mentions:
            channel_id = message.channel.id
            # Remove the mention from the message content
            content = message.content.replace(f'<@{bot.user.id}>', '').strip()
            add_message(channel_id, "user", message.author.name, content)
            history = get_history(channel_id, HISTORY_LIMIT)
            response = ask_ollama(history, os.getenv('OLLAMA_URL', 'http://plexllm-ollama-1:11434'))
            add_message(channel_id, "assistant", bot.user.name, response)
            await message.reply(response)
            return
        channel_id = message.channel.id
        add_message(channel_id, "user", message.author.name, message.content)
        await bot.process_commands(message)
