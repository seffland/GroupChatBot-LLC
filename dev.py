import os
import discord
from discord import app_commands
import sqlite3

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')
PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')

def add_dev_commands(bot):
    @bot.tree.command(
        name="db_size",
        description="Show how many items are in the history.db database",
        guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None
    )
    async def db_size(interaction: discord.Interaction):
        db_path = os.getenv("DB_PATH", "data/history.db")
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM messages")
                count = cursor.fetchone()[0]
            await interaction.response.send_message(f"There are {count} messages in the history.db database.")
        except Exception as e:
            await interaction.response.send_message(f"Error reading database: {e}")