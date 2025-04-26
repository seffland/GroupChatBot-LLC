import os
import requests
import discord
from discord import app_commands

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')

async def get_next_f1_race():
    """
    Fetches the next F1 race info from RacingCalendar.net API.
    Returns a string with the race name, location, and time.
    """
    import datetime
    url = "https://api.racingcalendar.net/events?series=f1&season=2025"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        events = resp.json()
        now = datetime.datetime.utcnow().date()
        next_race = None
        for event in events:
            event_date = datetime.datetime.strptime(event['startDate'], "%Y-%m-%d").date()
            if event_date >= now:
                next_race = event
                break
        if not next_race:
            return "No upcoming F1 races found for the current season."
        name = next_race.get('name', 'Unknown')
        location = next_race.get('venue', {}).get('name', 'Unknown location')
        city = next_race.get('venue', {}).get('city', '')
        country = next_race.get('venue', {}).get('country', '')
        date = next_race.get('startDate', 'Unknown date')
        time = next_race.get('startTime', None)
        loc_str = f"{location} ({city}, {country})" if city or country else location
        if time:
            date_time_str = f"{date} at {time} UTC"
        else:
            date_time_str = date
        return f"The next F1 race is **{name}** at **{loc_str}** on **{date_time_str}**."
    except Exception as e:
        return f"Could not fetch F1 race info: {e}"

def add_dev_commands(bot):
    @bot.tree.command(name="f1", description="Show the location and time of the next F1 race", guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None)
    async def f1(interaction: discord.Interaction):
        await interaction.response.defer()
        info = await get_next_f1_race()
        await interaction.followup.send(info)
