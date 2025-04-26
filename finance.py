import os
import requests
import discord
from discord import app_commands

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')
PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')

def add_finance_commands(bot):
    @bot.tree.command(name="btc", description="Get the current price of Bitcoin (BTC)")
    async def btc(interaction: discord.Interaction):
        """Returns the current price of Bitcoin in USD."""
        await interaction.response.defer()
        try:
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10)
            data = response.json()
            price = data["bitcoin"]["usd"]
            price_str = f"{price:,}"
            await interaction.followup.send(f"Current BTC price: ${price_str} USD")
        except Exception as e:
            await interaction.followup.send(f"Error fetching BTC price: {e}")