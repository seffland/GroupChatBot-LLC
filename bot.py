import discord
from discord import app_commands
from discord.ext import commands
from ollama_client import ask_ollama
import os

TOKEN = os.getenv('DISCORD_TOKEN')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://host.docker.internal:11435')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(e)

# In-memory conversation history: {channel_id: [messages]}
conversation_history = {}
HISTORY_LIMIT = 1000  # Number of messages to keep per channel

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    channel_id = message.channel.id
    history = conversation_history.get(channel_id, [])
    history.append({"role": "user", "content": message.content})
    conversation_history[channel_id] = history[-HISTORY_LIMIT:]
    await bot.process_commands(message)

@bot.tree.command(name="chat", description="Chat with the CCP")
@app_commands.describe(message="Your message to the CCP")
async def chat(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    channel_id = interaction.channel_id
    # Get or create history for this channel
    history = conversation_history.get(channel_id, [])
    # Append the /chat message as a user message
    history.append({"role": "user", "content": message})
    history = history[-HISTORY_LIMIT:]
    response = ask_ollama(history, OLLAMA_URL)
    # Append bot response
    history.append({"role": "assistant", "content": response})
    conversation_history[channel_id] = history[-HISTORY_LIMIT:]
    await interaction.followup.send(response)

if __name__ == "__main__":
    bot.run(TOKEN)
