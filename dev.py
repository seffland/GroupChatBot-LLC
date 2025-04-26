import os
import requests
import discord
from discord import app_commands

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')

async def get_next_f1_race():
    """
    Fetches the next F1 event and race info from the Jolpi Ergast API.
    Returns a string with the next event (practice, sprint, qualifying) and the next race, with times in EST.
    """
    import datetime
    import pytz
    url = "https://api.jolpi.ca/ergast/f1/current.json"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        races = data['MRData']['RaceTable']['Races']
        now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        est = pytz.timezone('US/Eastern')
        next_event = None
        next_event_time = None
        next_event_type = None
        next_race = None
        next_race_time = None
        # Find next event (practice, sprint, qualifying)
        for race in races:
            # Check for all event types in order: First Practice, Second Practice, Third Practice, Sprint, Qualifying
            event_types = [
                ('FirstPractice', 'Practice 1'),
                ('SecondPractice', 'Practice 2'),
                ('ThirdPractice', 'Practice 3'),
                ('Sprint', 'Sprint'),
                ('Qualifying', 'Qualifying'),
            ]
            for key, label in event_types:
                event = race.get(key)
                if event and event.get('date') and event.get('time'):
                    dt_utc = datetime.datetime.strptime(event['date'] + ' ' + event['time'].replace('Z', ''), "%Y-%m-%d %H:%M:%S")
                    dt_utc = dt_utc.replace(tzinfo=datetime.timezone.utc)
                    if dt_utc > now:
                        if not next_event or dt_utc < next_event_time:
                            next_event = race
                            next_event_time = dt_utc
                            next_event_type = label
            # Find next race
            if race.get('date') and race.get('time'):
                dt_utc = datetime.datetime.strptime(race['date'] + ' ' + race['time'].replace('Z', ''), "%Y-%m-%d %H:%M:%S")
                dt_utc = dt_utc.replace(tzinfo=datetime.timezone.utc)
                if dt_utc > now:
                    if not next_race or dt_utc < next_race_time:
                        next_race = race
                        next_race_time = dt_utc
        if not next_event and not next_race:
            return "No upcoming F1 events or races found for the current season."
        msg = ""
        if next_event:
            event_circuit = next_event.get('Circuit', {})
            event_loc = event_circuit.get('circuitName', 'Unknown location')
            event_city = event_circuit.get('Location', {}).get('locality', '')
            event_country = event_circuit.get('Location', {}).get('country', '')
            event_loc_str = f"{event_loc} ({event_city}, {event_country})" if event_city or event_country else event_loc
            event_time_est = next_event_time.astimezone(est)
            event_time_str = event_time_est.strftime("%Y-%m-%d at %I:%M %p EST")
            msg += f"The next F1 event is **{next_event_type}** at **{event_loc_str}** on **{event_time_str}**.\n"
        if next_race:
            race_name = next_race.get('raceName', 'Unknown')
            race_circuit = next_race.get('Circuit', {})
            race_loc = race_circuit.get('circuitName', 'Unknown location')
            race_city = race_circuit.get('Location', {}).get('locality', '')
            race_country = race_circuit.get('Location', {}).get('country', '')
            race_loc_str = f"{race_loc} ({race_city}, {race_country})" if race_city or race_country else race_loc
            race_time_est = next_race_time.astimezone(est)
            race_time_str = race_time_est.strftime("%Y-%m-%d at %I:%M %p EST")
            msg += f"The next F1 race is **{race_name}** at **{race_loc_str}** on **{race_time_str}**."
        return msg.strip()
    except Exception as e:
        return f"Could not fetch F1 event info: {e}"

def add_dev_commands(bot):
    @bot.tree.command(name="f1", description="Show the location and time of the next F1 race", guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None)
    async def f1(interaction: discord.Interaction):
        await interaction.response.defer()
        info = await get_next_f1_race()
        await interaction.followup.send(info)
