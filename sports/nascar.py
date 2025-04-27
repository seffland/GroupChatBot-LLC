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

def get_last_nascar_cup_winner():
    """
    Fetch the most recent completed NASCAR Cup race and return the winner's name, race name, date, and location.
    Uses TheSportsDB API for reliability.
    Returns None if not found or on error.
    """
    import requests
    from datetime import datetime
    import pytz
    url = "https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4393&s=2025"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        events = data.get('events', [])
        now = datetime.now(pytz.utc)
        past_events = []
        for event in events:
            date_str = event.get('dateEvent')
            time_str = event.get('strTime')
            if not date_str:
                continue
            dt_str = date_str
            if time_str:
                dt_str += 'T' + time_str
            try:
                event_time = datetime.fromisoformat(dt_str)
                if event_time.tzinfo is None:
                    event_time = pytz.utc.localize(event_time)
            except Exception:
                event_time = datetime.strptime(date_str, "%Y-%m-%d")
                event_time = pytz.utc.localize(event_time)
            if event_time < now and event.get('strResult'):
                past_events.append((event_time, event))
        if not past_events:
            return None
        past_events.sort(key=lambda x: x[0], reverse=True)
        last_event_time, last_event = past_events[0]
        race_name = last_event.get('strEvent', 'Unknown race')
        result_str = last_event.get('strResult', '')
        winner = 'Unknown'
        if result_str:
            lines = [line.strip() for line in result_str.split('\n') if line.strip()]
            if lines:
                first_line = lines[0]
                parts = first_line.split('/')[1:]
                if parts:
                    winner = parts[0].strip()
        date = last_event.get('dateEvent')
        location = last_event.get('strVenue', 'Unknown location')
        return {
            'winner': winner or 'Unknown',
            'race': race_name,
            'date': date,
            'location': location
        }
    except Exception as e:
        print(f"[DEBUG] Exception in get_last_nascar_cup_winner: {e}")
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

    @bot.tree.command(
        name="nascar_winner",
        description="Show the winner of the most recent NASCAR Cup race (dev only)",
        guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None
    )
    async def nascar_winner(interaction: discord.Interaction):
        await interaction.response.defer()
        result = get_last_nascar_cup_winner()
        if result:
            await interaction.followup.send(f"{result['winner']} won the {result['race']} at {result['location']} on {result['date']}.")
        else:
            await interaction.followup.send("Could not fetch the last NASCAR Cup winner.")
