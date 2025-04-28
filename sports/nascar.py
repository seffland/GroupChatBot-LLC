import os
import requests
import discord
from datetime import datetime, timezone, timedelta
import pytz

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')
PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')

# Helper for cf.nascar.com API
def _get_next_nascar_race_cf(series_id):
    current_year = datetime.now().year
    url = f"https://cf.nascar.com/cacher/{current_year}/{series_id}/schedule.json"
    print(f"DEBUG: Fetching cf.nascar.com API URL: {url}")
    headers = {"User-Agent": "Mozilla/5.0"} # Good practice

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status() # Check for HTTP errors (like 404 if year/series invalid)
        data = resp.json()

        # Data is expected to be a list of race events
        if not isinstance(data, list):
            print(f"ERROR: Unexpected data format from {url}. Expected a list.")
            # print(f"DEBUG: Received data: {data}") # Uncomment for debugging
            return None

        now = datetime.now(timezone.utc)
        future_races = []

        for event in data:
            # Assuming 'race_type_id' == 1 signifies a race event
            # Adjust if the field name or value is different
            if event.get('race_type_id') == 1:
                start_time_str = event.get('start_time_utc') # Expecting Unix timestamp in milliseconds
                if not start_time_str:
                    continue

                try:
                    # Convert milliseconds timestamp to datetime
                    event_time_utc = datetime.fromtimestamp(int(start_time_str) / 1000, tz=timezone.utc)
                except (ValueError, TypeError):
                    print(f"Error parsing start_time_utc: {start_time_str}")
                    continue

                if event_time_utc > now:
                    race_name = event.get('event_name', 'Unknown Race')
                    track_name = event.get('track_name', 'Unknown Location')
                    future_races.append((event_time_utc, race_name, track_name))

        if not future_races:
            print(f"No future races found for series_id {series_id} in cf.nascar.com data for {current_year}.")
            # TODO: Optionally try next year?
            return None

        # Sort to find the soonest race
        future_races.sort(key=lambda x: x[0])
        next_event_time_utc, next_name, next_venue = future_races[0]

        # Convert to EST/EDT for display
        est = pytz.timezone('US/Eastern')
        event_time_est = next_event_time_utc.astimezone(est)
        formatted_date = event_time_est.strftime('%B %d, %Y at %I:%M %p %Z')

        return {
            'name': next_name,
            'venue': next_venue,
            'date': formatted_date
        }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching cf.nascar.com API for series_id {series_id}: {e}")
        # This will catch 4xx/5xx errors after resp.raise_for_status()
        return None
    except Exception as e:
        print(f"An unexpected error occurred in _get_next_nascar_race_cf: {e}")
        return None

def get_next_nascar_race(series="cup"):
    series_lower = series.lower()

    # Map user input to API specifics
    series_map = {
        "cup": {"api": "thesportsdb", "id": "4393"},
        "xfinity": {"api": "cf", "id": 2},
        "truck": {"api": "cf", "id": 3}
    }

    config = series_map.get(series_lower)

    if not config:
        print(f"Unsupported NASCAR series: {series}")
        return None

    if config["api"] == "cf":
        print(f"Using cf.nascar.com API for {series} (ID: {config['id']})...")
        return _get_next_nascar_race_cf(config['id'])

    elif config["api"] == "thesportsdb":
        print(f"Using TheSportsDB API for {series} (ID: {config['id']})...")
        league_id = config['id']
        # ... (Existing TheSportsDB logic) ...
        current_year = datetime.now().year
        url = f"https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id={league_id}&s={current_year}"
        headers = {"User-Agent": "Mozilla/5.0"}
        thesportsdb_result = None
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            events = data.get('events', [])

            if not events:
                print(f"No {series} events found in TheSportsDB for season {current_year}. Trying next year.")
                url_next_year = f"https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id={league_id}&s={current_year + 1}"
                resp_next = requests.get(url_next_year, headers=headers, timeout=10)
                resp_next.raise_for_status()
                data_next = resp_next.json()
                events = data_next.get('events', [])

            if events:
                now = datetime.now(timezone.utc)
                future_events = []
                for event in events:
                    date_str = event.get('dateEvent')
                    time_str = event.get('strTime')
                    name = event.get('strEvent', f'Unknown {series.capitalize()} Race')
                    venue_name = event.get('strVenue', 'Unknown location')

                    if not date_str:
                        continue

                    event_time_utc = None
                    try:
                        if time_str and time_str != "00:00:00":
                            full_dt_str = f"{date_str}T{time_str}Z"
                            if ":" in time_str and ("+" in time_str or "-" in time_str):
                                full_dt_str = f"{date_str}T{time_str}"
                                event_time_utc = datetime.fromisoformat(full_dt_str).astimezone(timezone.utc)
                            else:
                                event_time_utc = datetime.fromisoformat(full_dt_str.replace("Z", "+00:00"))
                        else:
                            event_time_utc = datetime.strptime(date_str, "%Y-%m-%d")
                            event_time_utc = pytz.utc.localize(event_time_utc)
                    except ValueError as e:
                        print(f"Error parsing TheSportsDB date/time for event '{name}': {date_str} {time_str}. Error: {e}")
                        continue

                    if event_time_utc > now:
                        future_events.append((event_time_utc, name, venue_name))

                if future_events:
                    future_events.sort(key=lambda x: x[0])
                    next_event_time_utc, next_name, next_venue = future_events[0]

                    est = pytz.timezone('US/Eastern')
                    event_time_est = next_event_time_utc.astimezone(est)
                    formatted_date = event_time_est.strftime('%B %d, %Y at %I:%M %p %Z')

                    thesportsdb_result = {
                        'name': next_name,
                        'venue': next_venue,
                        'date': formatted_date
                    }
                    print(f"Successfully found next {series} race via TheSportsDB.")
                else:
                    print(f"No future {series} events found in TheSportsDB schedule.")
            else:
                 print(f"No {series} events found in TheSportsDB for season {current_year} or {current_year + 1}.")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching TheSportsDB NASCAR {series} events: {e}")
        except Exception as e:
            print(f"An unexpected error occurred fetching {series} race via TheSportsDB: {e}")

        return thesportsdb_result
    else:
        # Should not be reached if series_map is correct
        print(f"Internal error: Unknown API configuration for series {series}")
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
            # Check if the event time is in the past, regardless of result availability
            if event_time < now:
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
        # Format date as MM-DD-YYYY
        if date:
            try:
                from datetime import datetime
                date = datetime.strptime(date, "%Y-%m-%d").strftime("%m-%d-%Y")
            except Exception:
                pass
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
    # Re-enable series choices
    SERIES_CHOICES = [
        app_commands.Choice(name='Cup', value='cup'),
        app_commands.Choice(name='Xfinity', value='xfinity'),
        app_commands.Choice(name='Truck', value='truck')
    ]
    @bot.tree.command(
        name="nascar",
        description="Show the location and time of the next NASCAR race", # General description again
    )
    # Re-add series choice
    @app_commands.describe(series="Select the NASCAR series")
    @app_commands.choices(series=SERIES_CHOICES)
    async def nascar_command(interaction: discord.Interaction, series: app_commands.Choice[str]):
        await interaction.response.defer()  # Defer immediately
        race = get_next_nascar_race(series.value)
        if race:
            # Format message, omitting venue if 'Unknown location'
            message = f"Next NASCAR {series.name} race: {race['name']}"
            # Use the venue name directly from the result, which defaults to 'Unknown Location' if needed
            if race['venue'] != 'Unknown Location' and race['venue'] != 'Unknown location': # Check against defaults
                message += f" at {race['venue']}"
            message += f" on {race['date']}"
            await interaction.followup.send(message)
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
