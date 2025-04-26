import discord
from discord import app_commands
from discord.ext import commands
from ollama_client import ask_ollama
from db import add_message, get_history, get_last_imported_message_id, set_last_imported_message_id, search_history, get_messages_after_user_last, message_count, get_messages_for_timeframe
import os
import requests
from dev import add_dev_commands
from f1 import add_f1_command

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
        response = ask_ollama(history, OLLAMA_URL)
        add_message(channel_id, "assistant", bot.user.name, response)
        await message.reply(response)
        return
    channel_id = message.channel.id
    add_message(channel_id, "user", message.author.name, message.content)
    await bot.process_commands(message)

@bot.tree.command(name="chat", description="Chat with the llama")
@app_commands.describe(message="Your message to the llama")
async def chat(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    channel_id = interaction.channel_id
    add_message(channel_id, "user", interaction.user.name, message)
    history = get_history(channel_id, HISTORY_LIMIT)
    response = ask_ollama(history, OLLAMA_URL)
    add_message(channel_id, "assistant", bot.user.name, response)
    await interaction.followup.send(response)

@bot.tree.command(name="history", description="Show the conversation history for this channel")
async def history(interaction: discord.Interaction):
    await interaction.response.defer()
    channel_id = interaction.channel_id
    history = get_history(channel_id, HISTORY_LIMIT)
    if not history:
        await interaction.followup.send("No conversation history for this channel.")
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
    await interaction.followup.send(output)

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
    max_joy = max(user_joy_received.values())
    funniest_users = [user for user, count in user_joy_received.items() if count == max_joy]
    leaderboard = sorted(user_joy_received.items(), key=lambda x: x[1], reverse=True)
    leaderboard_str = '\n'.join([f"{i+1}. {user} - {count} :joy:" for i, (user, count) in enumerate(leaderboard)])
    if len(funniest_users) == 1:
        await interaction.followup.send(f"The funniest user is **{funniest_users[0]}** with {max_joy} :joy: reactions received!\n\nLeaderboard:\n{leaderboard_str}")
    else:
        users_str = ', '.join(f"**{user}**" for user in funniest_users)
        await interaction.followup.send(f"It's a tie! The funniest users are {users_str} with {max_joy} :joy: reactions received each!\n\nLeaderboard:\n{leaderboard_str}")

@bot.tree.command(name="stingy", description="Declare the stingiest user based on who gives out the least :joy: reactions in this channel")
@app_commands.describe(days="Number of days to look back, today, yesterday, or 'all' for all time")
async def stingy(interaction: discord.Interaction, days: str):
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
    user_joy_given = {}
    async for msg in channel.history(limit=None, oldest_first=True, after=after, before=before):
        for reaction in msg.reactions:
            is_joy = False
            if str(reaction.emoji) == '😂':
                is_joy = True
            elif hasattr(reaction.emoji, 'name') and reaction.emoji.name == 'joy':
                is_joy = True
            elif str(reaction.emoji) == ':joy:':
                is_joy = True
            if is_joy:
                users = []
                try:
                    users = [user async for user in reaction.users()]
                except Exception:
                    continue
                for user in users:
                    if user.bot:
                        continue
                    user_joy_given[user.name] = user_joy_given.get(user.name, 0) + 1
    if not user_joy_given:
        await interaction.followup.send("Everyone is stingy! No :joy: reactions were given in this channel for the given period.")
        return
    min_joy = min(user_joy_given.values())
    stingiest_users = [user for user, count in user_joy_given.items() if count == min_joy]
    leaderboard = sorted(user_joy_given.items(), key=lambda x: x[1])
    leaderboard_str = '\n'.join([f"{i+1}. {user} - {count} :joy:" for i, (user, count) in enumerate(leaderboard)])
    if len(stingiest_users) == 1:
        await interaction.followup.send(f"The stingiest user is **{stingiest_users[0]}** with only {min_joy} :joy: reactions given!\n\nLeaderboard (least to most):\n{leaderboard_str}")
    else:
        users_str = ', '.join(f"**{user}**" for user in stingiest_users)
        await interaction.followup.send(f"It's a tie! The stingiest users are {users_str} with only {min_joy} :joy: reactions given each!\n\nLeaderboard (least to most):\n{leaderboard_str}")

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
