import discord
from discord import app_commands
from discord.ext import commands
from ollama_client import ask_ollama
from db import add_message, get_history, get_last_imported_message_id, set_last_imported_message_id, search_history, get_messages_after_user_last, message_count
import os

TOKEN = os.getenv('DISCORD_TOKEN')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://plexllm-ollama-1:11434')
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
    # If the bot is mentioned, treat as a chat request
    if bot.user in message.mentions:
        channel_id = message.channel.id
        # Remove the mention from the message content
        content = message.content.replace(f'<@{bot.user.id}>', '').strip()
        add_message(channel_id, "user", message.author.name, content)
        history = get_history(channel_id, HISTORY_LIMIT)
        # Send the user's message as a chat
        await message.channel.send(f"**{message.author.name} (User):** {content}")
        response = ask_ollama(history, OLLAMA_URL)
        add_message(channel_id, "assistant", bot.user.name, response)
        await message.channel.send(response)
        return
    channel_id = message.channel.id
    add_message(channel_id, "user", message.author.name, message.content)
    await bot.process_commands(message)

@bot.tree.command(name="chat", description="Chat with the llama")
@app_commands.describe(message="Your message to the llama")
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

@bot.tree.command(name="search", description="Search the conversation history for a keyword in this channel")
@app_commands.describe(query="The keyword or phrase to search for")
async def search(interaction: discord.Interaction, query: str):
    channel_id = interaction.channel_id
    results = search_history(channel_id, query, limit=10)
    if not results:
        await interaction.response.send_message(f"No results found for '{query}'.")
        return
    formatted = []
    for msg in results:
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

@bot.tree.command(name="tldr", description="Summarize everything since you last sent a message in this channel (cleaned output)")
async def tldr(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    username = interaction.user.name
    messages = get_messages_after_user_last(channel_id, username)
    if not messages:
        await interaction.response.send_message("No new messages since your last message.")
        return
    summary_prompt = [{
        "role": "system",
        "content": "Summarize the following conversation for me. Be concise and to the point. 500 words or less please."
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

@bot.tree.command(name="message_count", description="Show how many messages have been sent in this channel in the last N days")
@app_commands.describe(days="Number of days to look back, today, yesterday, or 'all' for all time")
async def message_count_cmd(interaction: discord.Interaction, days: str):
    channel_id = interaction.channel_id
    if days.lower() == 'all':
        count = message_count(channel_id, 'all')
        await interaction.response.send_message(f"{count} messages have been sent all time in this channel.")
    elif days.lower() == 'today':
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        count = message_count(channel_id, 0)
        await interaction.response.send_message(f"{count} messages have been sent today in this channel.")
    elif days.lower() == 'yesterday':
        count = message_count(channel_id, 'yesterday')
        await interaction.response.send_message(f"{count} messages have been sent yesterday in this channel.")
    else:
        try:
            days_int = int(days)
            count = message_count(channel_id, days_int)
            await interaction.response.send_message(f"{count} messages have been sent in the last {days_int} day(s) in this channel.")
        except ValueError:
            await interaction.response.send_message("Please provide a number of days (e.g. 7), 'today', 'yesterday', or 'all'.")

@bot.tree.command(name="funniest", description="Declare the funniest user based on :joy: reactions in this channel")
@app_commands.describe(days="Number of days to look back, today, yesterday, or 'all' for all time")
async def funniest(interaction: discord.Interaction, days: str):
    channel = interaction.channel
    await interaction.response.defer(thinking=True)
    if days.lower() == 'all':
        after = None
        before = None
    elif days.lower() == 'today':
        from datetime import datetime, time, timezone
        try:
            from zoneinfo import ZoneInfo
            eastern = ZoneInfo('America/New_York')
        except ImportError:
            import pytz
            eastern = pytz.timezone('America/New_York')
        now_est = datetime.now(eastern)
        today_start_est = datetime.combine(now_est.date(), time(hour=0, minute=0), tzinfo=eastern)
        after = today_start_est.astimezone(timezone.utc)
        before = None
    elif days.lower() == 'yesterday':
        from datetime import datetime, time, timedelta, timezone
        try:
            from zoneinfo import ZoneInfo
            eastern = ZoneInfo('America/New_York')
        except ImportError:
            import pytz
            eastern = pytz.timezone('America/New_York')
        now_est = datetime.now(eastern)
        yesterday_date = now_est.date() - timedelta(days=1)
        y_start_est = datetime.combine(yesterday_date, time(hour=0, minute=0), tzinfo=eastern)
        y_end_est = datetime.combine(now_est.date(), time(hour=0, minute=0), tzinfo=eastern)
        after = y_start_est.astimezone(timezone.utc)
        before = y_end_est.astimezone(timezone.utc)
    else:
        try:
            days_int = int(days)
            from datetime import datetime, timedelta, timezone
            after = datetime.now(timezone.utc) - timedelta(days=days_int)
            before = None
        except ValueError:
            await interaction.followup.send("Please provide a number of days (e.g. 7), 'today', 'yesterday', or 'all'.")
            return
    user_joy_received = {}
    async for msg in channel.history(limit=None, oldest_first=True, after=after, before=before):
        joy_count = 0
        for reaction in msg.reactions:
            is_joy = False
            if str(reaction.emoji) == '😂':
                is_joy = True
            elif hasattr(reaction.emoji, 'name') and reaction.emoji.name == 'joy':
                is_joy = True
            elif str(reaction.emoji) == ':joy:':
                is_joy = True
            if is_joy:
                joy_count += reaction.count
        if joy_count > 0:
            user_joy_received[msg.author.name] = user_joy_received.get(msg.author.name, 0) + joy_count
    if not user_joy_received:
        await interaction.followup.send("No :joy: reactions found in this channel for the given period.")
        return
    funniest_user = max(user_joy_received, key=user_joy_received.get)
    funniest_count = user_joy_received[funniest_user]
    leaderboard = sorted(user_joy_received.items(), key=lambda x: x[1], reverse=True)
    leaderboard_str = '\n'.join([f"{i+1}. {user} - {count} :joy:" for i, (user, count) in enumerate(leaderboard)])
    await interaction.followup.send(f"The funniest user is **{funniest_user}** with {funniest_count} :joy: reactions received!\n\nLeaderboard:\n{leaderboard_str}")

if __name__ == "__main__":
    bot.run(TOKEN)
