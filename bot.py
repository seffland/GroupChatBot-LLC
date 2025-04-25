import discord
from discord import app_commands
from discord.ext import commands
from ollama_client import ask_ollama
from db import add_message, get_history, get_last_imported_message_id, set_last_imported_message_id
import os

TOKEN = os.getenv('DISCORD_TOKEN')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://host.docker.internal:11435')
HISTORY_LIMIT = 1000  # Number of messages to keep per channel

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

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    channel_id = message.channel.id
    add_message(channel_id, "user", message.author.name, message.content)
    await bot.process_commands(message)

@bot.tree.command(name="chat", description="Chat with the CCP")
@app_commands.describe(message="Your message to the CCP")
async def chat(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    channel_id = interaction.channel_id
    # Append the /chat message as a user message
    add_message(channel_id, "user", interaction.user.name, message)
    # Get history for this channel
    history = get_history(channel_id, HISTORY_LIMIT)
    # Send the user's message as a followup immediately
    await interaction.followup.send(f"**{interaction.user.name} (User):** {message}")
    response = ask_ollama(history, OLLAMA_URL)
    # Append bot response
    add_message(channel_id, "assistant", bot.user.name, response)
    await interaction.followup.send(response)

@bot.tree.command(name="history", description="Show the conversation history for this channel")
async def history(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    history = get_history(channel_id, HISTORY_LIMIT)
    if not history:
        await interaction.response.send_message("No conversation history for this channel.")
        return
    # Format history as a readable string
    formatted = []
    for msg in history:
        role = msg.get("role", "user")
        username = msg.get("username", "user")
        content = msg.get("content", "")
        formatted.append(f"**{username} ({role.capitalize()}):** {content}")
    output = "\n".join(formatted)
    # Discord message limit is 2000 chars
    if len(output) > 1900:
        output = output[-1900:]
        output = "...\n" + output
    await interaction.response.send_message(output)

@bot.tree.command(name="import_history", description="Import all previous messages from this channel into the database (safe against duplicates)")
async def import_history(interaction: discord.Interaction):
    channel = interaction.channel
    channel_id = channel.id
    await interaction.response.defer(thinking=True, ephemeral=True)
    last_imported_id = get_last_imported_message_id(channel_id)
    imported = 0
    last_seen_id = last_imported_id
    async for msg in channel.history(limit=None, oldest_first=True, after=None):
        if last_imported_id and msg.id <= last_imported_id:
            continue
        if msg.author.bot:
            continue
        add_message(channel_id, "user", msg.author.name, msg.content)
        imported += 1
        last_seen_id = msg.id
    if imported > 0 and last_seen_id:
        set_last_imported_message_id(channel_id, last_seen_id)
    await interaction.followup.send(f"Imported {imported} new messages from this channel.")

if __name__ == "__main__":
    bot.run(TOKEN)
