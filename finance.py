import os
import requests
import discord
from discord import app_commands

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')
PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')

def add_finance_commands(bot):
    @bot.tree.command(name="btc", description="Get the current price of Bitcoin (BTC)")
    async def btc(interaction: discord.Interaction):
        """Returns the current price of Bitcoin in USD and 24h percent change."""
        await interaction.response.defer()
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
            response = requests.get(url, timeout=10)
            data = response.json()
            price = data["bitcoin"]["usd"]
            change = data["bitcoin"].get("usd_24h_change", None)
            price_str = f"{price:,}"
            if change is not None:
                change_str = f"{change:+.2f}%"
                await interaction.followup.send(f"Current BTC price: ${price_str} USD ({change_str} 24h)")
            else:
                await interaction.followup.send(f"Current BTC price: ${price_str} USD (24h change unavailable)")
        except Exception as e:
            await interaction.followup.send(f"Error fetching BTC price: {e}")