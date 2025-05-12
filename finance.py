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

    @bot.tree.command(name="ath", description="Announce you hit an all time high on net worth!")
    async def ath(interaction: discord.Interaction):
        """Announces a user's all time high, shows a gif, and the last time they hit an ATH."""
        import db
        from datetime import datetime
        try:
            from zoneinfo import ZoneInfo
            eastern = ZoneInfo('America/New_York')
        except ImportError:
            import pytz
            eastern = pytz.timezone('America/New_York')
        now_utc = datetime.utcnow()
        now_est = now_utc.replace(tzinfo=None).astimezone(eastern) if hasattr(now_utc, 'astimezone') else now_utc
        now_str = now_est.strftime('%m/%d/%Y')
        await interaction.response.defer()
        user_id = interaction.user.id
        username = interaction.user.display_name
        last_ath = db.get_user_ath(user_id)
        db.set_user_ath(user_id, username, now_str)
        gif_url = "https://tenor.com/view/kucoin-kcs-ethereum-eth-bitcoin-gif-18569399"
        if last_ath:
            # Parse last_ath as MM/DD/YYYY or fallback to just show 'unknown' if parsing fails
            from datetime import datetime, timedelta
            try:
                last_ath_dt = datetime.strptime(last_ath, '%m/%d/%Y')
                now_dt = datetime.strptime(now_str, '%m/%d/%Y')
                delta = now_dt - last_ath_dt
                days = delta.days
                hours = delta.seconds // 3600
                minutes = (delta.seconds % 3600) // 60
                ago_str = f"{days}d {hours}h {minutes}m ago" if days or hours or minutes else "just now"
            except Exception:
                ago_str = "unknown"
            msg = f"<@{user_id}> just hit a new ALL TIME HIGH on net worth! 🚀\nLast ATH: {ago_str}"
        else:
            msg = f"<@{user_id}> just hit their FIRST ALL TIME HIGH on net worth! 🚀"
        await interaction.followup.send(msg)
        await interaction.followup.send(gif_url)