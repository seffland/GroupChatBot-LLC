import os
import requests
import discord
from discord import app_commands

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')
PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')

async def get_next_f1_race():
    import datetime
    import pytz
    url = "http://sports.core.api.espn.com/v2/sports/racing/leagues/f1/events?season=2025"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get('items', [])
        if not items:
            return "No F1 events found for the current season."
        now = datetime.datetime.now(datetime.timezone.utc)
        est = pytz.timezone('US/Eastern')
        event_list = []
        for event_ref in items:
            if isinstance(event_ref, dict):
                date_str = event_ref.get('date')
                name = event_ref.get('name', 'Unknown event')
                venues = event_ref.get('venues', [])
                event_url = event_ref.get('$ref')
            else:
                date_str = None
                name = 'Unknown event'
                venues = []
                event_url = event_ref
            if not date_str and event_url:
                try:
                    event_resp = requests.get(event_url, timeout=10)
                    event_resp.raise_for_status()
                    event_data = event_resp.json()
                    date_str = event_data.get('date')
                    name = event_data.get('name', name)
                    venues = event_data.get('venues', venues)
                except Exception as event_exc:
                    continue
            if not date_str:
                continue
            event_time = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            event_list.append((event_time, name, venues))
        event_list.sort(key=lambda x: x[0])
        for event_time, name, venues in event_list:
            if event_time > now:
                venue_name = 'Unknown location'
                if venues and isinstance(venues[0], dict) and '$ref' in venues[0]:
                    try:
                        venue_resp = requests.get(venues[0]['$ref'], timeout=10)
                        venue_resp.raise_for_status()
                        venue_data = venue_resp.json()
                        venue_name = venue_data.get('fullName', 'Unknown location')
                    except Exception:
                        pass
                event_time_est = event_time.astimezone(est)
                formatted_date = event_time_est.strftime('%B %d, %Y at %I:%M %p EST')
                return f"The next F1 race is **{name}** at **{venue_name}** on **{formatted_date}**."
        # If no future event, return the last event
        if event_list:
            last_event_time, last_name, last_venues = event_list[-1]
            venue_name = 'Unknown location'
            if last_venues and isinstance(last_venues[0], dict) and '$ref' in last_venues[0]:
                try:
                    venue_resp = requests.get(last_venues[0]['$ref'], timeout=10)
                    venue_resp.raise_for_status()
                    venue_data = venue_resp.json()
                    venue_name = venue_data.get('fullName', 'Unknown location')
                except Exception:
                    pass
            last_event_time_est = last_event_time.astimezone(est)
            formatted_date = last_event_time_est.strftime('%B %d, %Y at %I:%M %p EST')
            return f"The last F1 race was **{last_name}** at **{venue_name}** on **{formatted_date}**."
        return "No F1 events found for the current season."
    except Exception as e:
        return f"Could not fetch F1 event info: {e}"

def add_dev_commands(bot):
    @bot.tree.command(
        name="f1_dev",
        description="Show the location and time of the next F1 race",
        guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None
    )
    async def f1(interaction: discord.Interaction):
        await interaction.response.defer()
        info = await get_next_f1_race()
        await interaction.followup.send(info)

    @bot.tree.command(
        name="f1_next_event",
        description="Show the next F1 event period (practice, qualifying, race, etc.)",
        guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None
    )
    async def f1_next_event(interaction: discord.Interaction):
        await interaction.response.defer()
        info = await get_next_f1_event_period()
        await interaction.followup.send(info)

async def get_next_f1_event_period():
    import datetime
    import pytz
    url = "http://sports.core.api.espn.com/v2/sports/racing/leagues/f1/events?season=2025"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get('items', [])
        if not items:
            return "No F1 events found for the current season."
        now = datetime.datetime.now(datetime.timezone.utc)
        est = pytz.timezone('US/Eastern')
        event_list = []
        for event_ref in items:
            if isinstance(event_ref, dict):
                date_str = event_ref.get('date')
                name = event_ref.get('name', 'Unknown event')
                venues = event_ref.get('venues', [])
                event_url = event_ref.get('$ref')
                event_type = event_ref.get('type', {}).get('description', 'Event')
            else:
                date_str = None
                name = 'Unknown event'
                venues = []
                event_url = event_ref
                event_type = 'Event'
            if not date_str and event_url:
                try:
                    event_resp = requests.get(event_url, timeout=10)
                    event_resp.raise_for_status()
                    event_data = event_resp.json()
                    date_str = event_data.get('date')
                    name = event_data.get('name', name)
                    venues = event_data.get('venues', venues)
                    event_type = event_data.get('type', {}).get('description', event_type)
                except Exception:
                    continue
            if not date_str:
                continue
            event_time = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            event_list.append((event_time, name, venues, event_type))
        event_list.sort(key=lambda x: x[0])
        for event_time, name, venues, event_type in event_list:
            if event_time > now:
                venue_name = 'Unknown location'
                if venues and isinstance(venues[0], dict) and '$ref' in venues[0]:
                    try:
                        venue_resp = requests.get(venues[0]['$ref'], timeout=10)
                        venue_resp.raise_for_status()
                        venue_data = venue_resp.json()
                        venue_name = venue_data.get('fullName', 'Unknown location')
                    except Exception:
                        pass
                event_time_est = event_time.astimezone(est)
                formatted_date = event_time_est.strftime('%B %d, %Y at %I:%M %p EST')
                return f"The next F1 event is **{name}** (**{event_type}**) at **{venue_name}** on **{formatted_date}**."
        return "No upcoming F1 events found for the current season."
    except Exception as e:
        return f"Could not fetch F1 event info: {e}"