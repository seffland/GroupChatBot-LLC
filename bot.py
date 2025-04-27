import discord
from discord import app_commands
from discord.ext import commands
from ollama_client import ask_ollama
from db import add_message, get_history, get_last_imported_message_id, set_last_imported_message_id, search_history, get_messages_after_user_last, message_count, get_messages_for_timeframe
import os
import asyncio
from dev import add_dev_commands
from f1 import add_f1_command
from finance import add_finance_commands
from nascar import add_nascar_commands
from on_message import setup_on_message
from reactions import add_reaction_commands
from historian import add_historian_commands

TOKEN = os.getenv('DISCORD_TOKEN')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://plexllm-ollama-1:11434')
HISTORY_LIMIT = 1000  # Number of messages to keep per channel
DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')
PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

add_f1_command(bot)
add_dev_commands(bot)
add_finance_commands(bot)
add_nascar_commands(bot)
add_reaction_commands(bot)
add_historian_commands(bot)
setup_on_message(bot, HISTORY_LIMIT)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        # Always sync to the development server for fast iteration,
        # but also sync globally if PRODUCTION_SERVER_ID is set.
        if DEVELOPMENT_SERVER_ID:
            guild_obj = discord.Object(id=int(DEVELOPMENT_SERVER_ID))
            synced = await bot.tree.sync(guild=guild_obj)
            print(f'Synced {len(synced)} command(s) to development server {DEVELOPMENT_SERVER_ID}')
        if PRODUCTION_SERVER_ID:
            # Optionally sync to a production server for testing before global
            prod_guild_obj = discord.Object(id=int(PRODUCTION_SERVER_ID))
            synced_prod = await bot.tree.sync(guild=prod_guild_obj)
            print(f'Synced {len(synced_prod)} command(s) to production server {PRODUCTION_SERVER_ID}')
        # Always sync globally as well
        synced_global = await bot.tree.sync()
        print(f'Synced {len(synced_global)} command(s) globally')
    except Exception as e:
        print("Error during command sync:", e)

@bot.tree.command(name="chat", description="Chat with the llama")
@app_commands.describe(message="Your message to the llama")
async def chat(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    channel_id = interaction.channel_id
    add_message(channel_id, "user", interaction.user.name, message)
    history = get_history(channel_id, HISTORY_LIMIT)
    try:
        response = await asyncio.to_thread(ask_ollama, history, OLLAMA_URL)
    except Exception as e:
        response = f"Error: {e}"
    add_message(channel_id, "assistant", bot.user.name, response)
    await interaction.followup.send(response)

@bot.tree.command(name="tldr", description="Summarize everything since you last sent a message in this channel")
async def tldr(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    username = interaction.user.name
    messages = get_messages_after_user_last(channel_id, username)
    if not messages:
        await interaction.response.send_message("No new messages since your last message.")
        return
    summary_prompt = [{
        "role": "system",
        "content": "Summarize the following conversation for me. Be concise and to the point. 50 words or less please."
    }] + messages
    await interaction.response.defer()
    summary = ask_ollama(summary_prompt, OLLAMA_URL)
    import re
    # Remove all <think>...</think>, <think>, and </think> tags anywhere in the text
    summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL)
    summary = re.sub(r'<think>|</think>', '', summary)
    summary = summary.strip()
    # Truncate to Discord's message limit (2000 chars, use 1900 for safety)
    if len(summary) > 1900:
        summary = summary[:1900] + "..."
    await interaction.followup.send(f"**TL;DR:**\n{summary}")

@bot.tree.command(name="summarize", description="Summarize all messages in this channel for a given timeframe (today, yesterday, this_month, all)")
@app_commands.describe(timeframe="Timeframe to summarize: today, yesterday, this_month, or all")
async def summarize(interaction: discord.Interaction, timeframe: str):
    channel_id = interaction.channel_id
    valid_timeframes = {"today", "yesterday", "this_month", "all"}
    if timeframe not in valid_timeframes:
        await interaction.response.send_message("Please provide a valid timeframe: today, yesterday, this_month, or all.")
        return
    messages = get_messages_for_timeframe(channel_id, timeframe)
    if not messages:
        await interaction.response.send_message(f"No messages found for timeframe '{timeframe}'.")
        return
    summary_prompt = [{
        "role": "system",
        "content": f"Summarize the following conversation for the timeframe '{timeframe}'. Be concise and to the point. 500 words or less."
    }] + messages
    await interaction.response.defer()
    summary = ask_ollama(summary_prompt, OLLAMA_URL)
    import re
    summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL)
    summary = re.sub(r'<think>|</think>', '', summary)
    summary = summary.strip()
    if len(summary) > 1900:
        summary = summary[:1900] + "..."
    await interaction.followup.send(f"**Summary for {timeframe}:**\n{summary}")

@bot.tree.context_menu(name="ELI5 (Explain Like I'm 5)")
async def eli5(interaction: discord.Interaction, message: discord.Message):
    """
    Explains the selected message like the user is 5 years old using the LLM.
    """
    await interaction.response.defer()
    prompt = [
        {"role": "system", "content": "Explain the following message as if you are talking to a 5-year-old. Use simple words and keep it short."},
        {"role": "user", "content": message.content}
    ]
    explanation = ask_ollama(prompt, OLLAMA_URL)
    import re
    explanation = re.sub(r'<think>.*?</think>', '', explanation, flags=re.DOTALL)
    explanation = re.sub(r'<think>|</think>', '', explanation)
    explanation = explanation.strip()
    if len(explanation) > 1900:
        explanation = explanation[:1900] + "..."
    # Show the original message and the ELI5 explanation
    await interaction.followup.send(f"**Original message:**\n> {message.content}\n\n**ELI5:**\n{explanation}", ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)
