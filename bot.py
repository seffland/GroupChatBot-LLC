import discord
from discord import app_commands
from discord.ext import commands
from ollama_client import ask_ollama
import os

TOKEN = os.getenv('DISCORD_TOKEN')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://ollama:11434')

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

@bot.tree.command(name="chat", description="Chat with Ollama")
@app_commands.describe(message="Your message to Ollama")
async def chat(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    response = ask_ollama(message, OLLAMA_URL)
    await interaction.followup.send(response)

if __name__ == "__main__":
    bot.run(TOKEN)
