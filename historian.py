import discord
from db import get_history, add_message, get_last_imported_message_id, set_last_imported_message_id, search_history, message_count
import os
from db import add_quote, get_quotes

def add_historian_commands(bot):
    @bot.tree.command(name="history", description="Show the conversation history for this channel")
    async def history(interaction: discord.Interaction):
        channel_id = getattr(interaction, "channel_id", None)
        if channel_id is None:
            await interaction.followup.send("Could not determine channel ID.")
            return
        history = get_history(channel_id, 1000)
        if not history:
            await interaction.followup.send("No conversation history for this channel.")
            return
        formatted = []
        for msg in history:
            role = msg.get("role", "user")
            username = msg.get("username", "user")
            content = msg.get("content", "")
            formatted.append(f"**{username} ({role.capitalize()}):** {content}")
        output = "\n".join(formatted)
        if len(output) > 1900:
            output = output[-1900:]
            output = "...\n" + output
        await interaction.followup.send(output)

    @bot.tree.command(name="import_history", description="Import all previous messages from this channel into the database (safe against duplicates)")
    async def import_history(interaction: discord.Interaction):
        owner_user_id_str = os.getenv("OWNER_USER_ID")
        if owner_user_id_str is None:
            await interaction.response.send_message("OWNER_USER_ID environment variable is not set.", ephemeral=True)
            return
        OWNER_USER_ID = int(owner_user_id_str)
        if interaction.user.id != OWNER_USER_ID:
            await interaction.response.send_message("You are not authorized to run this command.", ephemeral=True)
            return
        channel = getattr(interaction, "channel", None)
        if channel is None or not hasattr(channel, "history"):
            await interaction.response.send_message("This command can only be used in a text channel.", ephemeral=True)
            return
        channel_id = getattr(channel, "id", None)
        if channel_id is None:
            await interaction.response.send_message("Could not determine channel ID.", ephemeral=True)
            return
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
    @discord.app_commands.describe(query="The keyword or phrase to search for")
    async def search(interaction: discord.Interaction, query: str):
        channel_id = getattr(interaction, "channel_id", None)
        if channel_id is None:
            await interaction.response.send_message("Could not determine channel ID.")
            return
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
        if len(output) > 1900:
            output = output[-1900:]
            output = "...\n" + output
        await interaction.response.send_message(output)

    @bot.tree.command(name="message_count", description="Show how many messages have been sent in this channel in the last N days")
    @discord.app_commands.describe(days="Number of days to look back, today, yesterday, or 'all' for all time")
    async def message_count_cmd(interaction: discord.Interaction, days: str):
        channel_id = getattr(interaction, "channel_id", None)
        if channel_id is None:
            await interaction.response.send_message("Could not determine channel ID.")
            return
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

    @bot.tree.context_menu(name="Quote to Hall of Fame")
    async def quote_to_hof(interaction: discord.Interaction, message: discord.Message):
        channel = getattr(interaction, "channel", None)
        if channel is None or not hasattr(channel, "id"):
            await interaction.response.send_message("Could not determine channel ID.", ephemeral=True)
            return
        channel_id = channel.id
        add_quote(channel_id, message.id, message.author.name, message.content, interaction.user.name)
        await interaction.response.send_message(f"Quoted {message.author.name}: '{message.content[:100]}...' to the Hall of Fame!", ephemeral=True)

    @bot.tree.command(name="quote", description="Show recent Hall of Fame quotes for this channel")
    async def quote(interaction: discord.Interaction):
        channel_id = getattr(interaction, "channel_id", None)
        if channel_id is None:
            await interaction.response.send_message("Could not determine channel ID.")
            return
        quotes = get_quotes(channel_id, limit=5)
        if not quotes:
            await interaction.response.send_message("No Hall of Fame quotes yet for this channel.")
            return
        formatted = []
        for q in quotes:
            formatted.append(f"**{q['username']}**: \"{q['content']}\"\n_Quoted by {q['quoted_by']} on {q['timestamp']}_")
        output = "\n\n".join(formatted)
        await interaction.response.send_message(output)
