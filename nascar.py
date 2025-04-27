import os
import requests
import discord
from discord import app_commands

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')
PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')

SERIES_MAP = {
    'Cup': 1,
    'Xfinity': 2,
    'Truck': 3
}

SERIES_CHOICES = [
    app_commands.Choice(name='Cup', value='Cup'),
    app_commands.Choice(name='Xfinity', value='Xfinity'),
    app_commands.Choice(name='Truck', value='Truck')
]

def get_next_nascar_race(series_id):
    url = f"https://cf.nascar.com/cacher/2025/{series_id}/races.json"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        races = resp.json()
        print(f"Fetched {len(races)} races from {url}")  # DEBUG
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        for race in races:
            print(f"Checking race: {race}")  # DEBUG
            # Assume 'date' is in ISO format and UTC
            try:
                race_time = datetime.fromisoformat(race['date'].replace('Z', '+00:00'))
                print(f"Parsed race_time: {race_time}, now: {now}")  # DEBUG
                if race_time > now:
                    print(f"Next race found: {race}")  # DEBUG
                    return race
            except Exception as parse_exc:
                print(f"Failed to parse date for race: {race}, error: {parse_exc}")  # DEBUG
        print("No upcoming race found.")  # DEBUG
        return None
    except Exception as e:
        print(f"Error fetching races: {e}")  # DEBUG
        return None

def add_nascar_commands(bot):
    @bot.tree.command(
        name="nascar",
        description="Show the location and time of the next NASCAR race",
        guild=discord.Object(id=DEVELOPMENT_SERVER_ID) if DEVELOPMENT_SERVER_ID else None
    )
    @app_commands.describe(series="Select the NASCAR series")
    @app_commands.choices(series=SERIES_CHOICES)
    async def nascar_command(interaction: discord.Interaction, series: app_commands.Choice[str]):
        series_id = SERIES_MAP.get(series.value)
        race = get_next_nascar_race(series_id)
        if race:
            location = race.get('venue', 'Unknown location')
            date = race.get('date', 'Unknown date')
            name = race.get('name', 'Unknown race')
            await interaction.response.send_message(f"Next {series.value} race: {name} at {location} on {date}")
        else:
            await interaction.response.send_message(f"Could not find the next {series.value} race.")
