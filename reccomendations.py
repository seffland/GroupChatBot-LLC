# Group chat TV show recommendations command for Discord
import discord
from discord import app_commands
from discord.ext import commands

# Example data structure for recommendations (replace with DB or persistent storage as needed)
RECOMMENDATIONS = [
    {"title": "Severance", "watched_by": ["Alice", "Bob"]},
    {"title": "The Bear", "watched_by": ["Charlie"]},
    {"title": "Dark", "watched_by": ["Alice", "Eve", "Frank"]},
    {"title": "The Expanse", "watched_by": ["Bob", "Eve"]},
]

def add_recommendations_command(bot: commands.Bot):
    @bot.tree.command(name="reccomendations", description="Show group chat recommended TV shows and who has watched them.")
    async def reccomendations_command(interaction: discord.Interaction):
        embed = discord.Embed(title="Group TV Show Recommendations", color=discord.Color.blue())
        for rec in RECOMMENDATIONS:
            viewers = ", ".join(rec["watched_by"]) if rec["watched_by"] else "No one yet!"
            embed.add_field(name=rec["title"], value=f"Watched by: {viewers}", inline=False)
        await interaction.response.send_message(embed=embed)
