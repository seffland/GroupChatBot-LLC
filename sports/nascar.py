import os
import requests
import discord
from datetime import datetime, timezone

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')
PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')

def get_next_nascar_race(series="cup"):
    series_map = {
        "cup": "nascar-premier",
        "xfinity": "nascar-secondary",
        "truck": "nascar-truck"
    }
    league = series_map.get(series.lower(), "nascar-premier")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        if series.lower() == "xfinity":
            # Use direct events endpoint for Xfinity series
            url = "https://sports.core.api.espn.com/v2/sports/racing/leagues/nascar-secondary/events?season=2025"
        elif series.lower() == "truck":
            url = "https://sports.core.api.espn.com/v2/sports/racing/leagues/nascar-truck/events?season=2025"
        else:
            url = f"https://sports.core.api.espn.com/v2/sports/racing/leagues/{league}/events?season=2025"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get('items', [])
        if not items:
            print("No events found in ESPN API response.")
            return None
        now = datetime.now(timezone.utc)
        event_list = []
        for i, event_ref in enumerate(items):
            if isinstance(event_ref, dict):
                date_str = event_ref.get('date')
                name = event_ref.get('name', 'Unknown race')
                venues = event_ref.get('venues', [])
                event_url = event_ref.get('$ref')
            else:
                print(f"DEBUG: Event {i}: {event_ref}")
                date_str = None
                name = 'Unknown race'
                venues = []
                event_url = event_ref
            if not date_str and event_url:
                # Fallback: fetch event details if date is missing
                try:
                    event_resp = requests.get(event_url, headers=headers, timeout=10)
                    event_resp.raise_for_status()
                    event_data = event_resp.json()
                    date_str = event_data.get('date')
                    name = event_data.get('name', name)
                    venues = event_data.get('venues', venues)
                except Exception as event_exc:
                    print(f"Failed to process event: {event_url}, error: {event_exc}")
                    continue
            if not date_str:
                continue
            event_time = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            event_list.append((event_time, name, venues))
        event_list.sort(key=lambda x: x[0])
        for event_time, name, venues in event_list:
            if event_time > now:
                venue_name = 'Unknown location'
                if venues and isinstance(venues[0], dict) and '$ref' in venues[0]:
                    try:
                        venue_resp = requests.get(venues[0]['$ref'], headers=headers, timeout=10)
                        venue_resp.raise_for_status()
                        venue_data = venue_resp.json()
                        venue_name = venue_data.get('fullName', 'Unknown location')
                    except Exception as venue_exc:
                        print(f"Failed to fetch venue: {venues[0]['$ref']}, error: {venue_exc}")
                import pytz
                est = pytz.timezone('US/Eastern')
                event_time_est = event_time.astimezone(est)
                formatted_date = event_time_est.strftime('%B %d, %Y at %I:%M %p EST')
                return {
                    'name': name,
                    'venue': venue_name,
                    'date': formatted_date
                }
        # If no future event is found, return the last event (most recent past event)
        if event_list:
            last_event_time, last_name, last_venues = event_list[-1]
            venue_name = 'Unknown location'
            if last_venues and isinstance(last_venues[0], dict) and '$ref' in last_venues[0]:
                try:
                    venue_resp = requests.get(last_venues[0]['$ref'], headers=headers, timeout=10)
                    venue_resp.raise_for_status()
                    venue_data = venue_resp.json()
                    venue_name = venue_data.get('fullName', 'Unknown location')
                except Exception as venue_exc:
                    print(f"Failed to fetch venue: {last_venues[0]['$ref']}, error: {venue_exc}")
            import pytz
            est = pytz.timezone('US/Eastern')
            last_event_time_est = last_event_time.astimezone(est)
            formatted_date = last_event_time_est.strftime('%B %d, %Y at %I:%M %p EST')
            return {
                'name': last_name,
                'venue': venue_name,
                'date': formatted_date
            }
        print("No events found at all.")
        return None
    except Exception as e:
        print(f"Error fetching ESPN NASCAR events: {e}")
        return None

def add_nascar_commands(bot):
    from discord import app_commands
    SERIES_CHOICES = [
        app_commands.Choice(name='Cup', value='cup'),
        app_commands.Choice(name='Xfinity', value='xfinity'),
        app_commands.Choice(name='Truck', value='truck')
    ]
    @bot.tree.command(
        name="nascar",
        description="Show the location and time of the next NASCAR race",
    )
    @app_commands.describe(series="Select the NASCAR series")
    @app_commands.choices(series=SERIES_CHOICES)
    async def nascar_command(interaction: discord.Interaction, series: app_commands.Choice[str]):
        await interaction.response.defer()  # Defer immediately to avoid 404 error
        race = get_next_nascar_race(series.value)
        if race:
            await interaction.followup.send(f"Next NASCAR {series.name} race: {race['name']} at {race['venue']} on {race['date']}")
        else:
            await interaction.followup.send(f"Could not find the next NASCAR {series.name} race.")
