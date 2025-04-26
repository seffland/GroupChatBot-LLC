import os
import requests
import discord
from discord import app_commands

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')

async def get_next_f1_race():
    """
    Fetches the next F1 race info from the Ergast Developer API.
    Returns a string with the race name, location, and time.
    """
    import datetime
    url = "https://api.jolpi.ca/ergast/f1/current.json"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        races = data['MRData']['RaceTable']['Races']
        now = datetime.datetime.utcnow().date()
        next_race = None
        for race in races:
            race_date = datetime.datetime.strptime(race['date'], "%Y-%m-%d").date()
            if race_date >= now:
                next_race = race
                break
        if not next_race:
            return "No upcoming F1 races found for the current season."
        name = next_race.get('raceName', 'Unknown')
        circuit = next_race.get('Circuit', {})
        location = circuit.get('circuitName', 'Unknown location')
        loc_info = circuit.get('Location', {})
        city = loc_info.get('locality', '')
        country = loc_info.get('country', '')
        date = next_race.get('date', 'Unknown date')
        time = next_race.get('time', None)
        loc_str = f"{location} ({city}, {country})" if city or country else location
        if time:
            # Ergast time is in UTC and formatted as HH:MM:SSZ
            time_str = time.replace('Z', '')[:5]
            date_time_str = f"{date} at {time_str} UTC"
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
