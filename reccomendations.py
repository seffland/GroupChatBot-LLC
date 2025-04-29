# Group chat TV show recommendations command for Discord
import discord
from discord import app_commands
from discord.ext import commands
import db

def add_recommendations_command(bot: commands.Bot):
    @bot.tree.command(name="reccomendations", description="Show group chat recommended TV shows and who has watched them.")
    async def reccomendations_command(interaction: discord.Interaction):
        recs = db.get_recommendations_with_watchers()
        embed = discord.Embed(title="Group TV Show Recommendations", color=discord.Color.blue())
        for rec in recs:
            viewers = ", ".join(rec["watched_by"]) if rec["watched_by"] else "No one yet!"
            embed.add_field(name=rec["title"], value=f"Watched by: {viewers}", inline=False)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="addrec", description="Add a new TV show recommendation.")
    @app_commands.describe(title="The title of the TV show to recommend.")
    async def addrec_command(interaction: discord.Interaction, title: str):
        db.add_recommendation(title)
        await interaction.response.send_message(f"Added recommendation: {title}")

    async def tv_title_autocomplete(interaction: discord.Interaction, current: str):
        # Fetch all TV show titles from the database
        recs = db.get_recommendations_with_watchers()
        # Filter by what the user has typed so far (case-insensitive)
        return [
            app_commands.Choice(name=rec["title"], value=rec["title"])
            for rec in recs if current.lower() in rec["title"].lower()
        ][:25]  # Discord allows max 25 choices

    @bot.tree.command(name="watched", description="Mark a TV show as watched by you.")
    @app_commands.describe(title="The title of the TV show you have watched.")
    @app_commands.autocomplete(title=tv_title_autocomplete)
    async def watched_command(interaction: discord.Interaction, title: str):
        username = interaction.user.name  # Always use global Discord username for consistency
        try:
            db.mark_recommendation_watched(title, username)
            await interaction.response.send_message(f"Marked '{title}' as watched for {username}.")
        except ValueError:
            await interaction.response.send_message(f"Recommendation '{title}' not found.", ephemeral=True)
