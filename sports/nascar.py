import os
import requests
import discord
from datetime import datetime, timezone, timedelta
import pytz

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')
PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')

def get_next_nascar_race(series="cup"):
    series_lower = series.lower()

    # Map user input to TheSportsDB league IDs
    # Cup: 4393, Xfinity: 4400, Truck: 4401
    series_map = {
        "cup": {"api": "thesportsdb", "id": "4393"},
        "xfinity": {"api": "thesportsdb", "id": "4573"}, # Use TheSportsDB
        "truck": {"api": "thesportsdb", "id": "5093"}  # Use TheSportsDB
    }

    config = series_map.get(series_lower)
    if not config:
        return None

    # Simplified: Always use TheSportsDB logic
    league_id = config['id']
    current_year = datetime.now().year
    # Try current year first
    url = f"https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id={league_id}&s={current_year}"
    headers = {"User-Agent": "Mozilla/5.0"} # Good practice
    thesportsdb_result = None

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        events = data.get('events', [])

        # If no events found for the current year, try the next year
        if not events:
            url_next_year = f"https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id={league_id}&s={current_year + 1}"
            resp_next = requests.get(url_next_year, headers=headers, timeout=10)
            # Allow 404 for next year's schedule if it doesn't exist yet
            if resp_next.status_code == 404:
                events = []
            else:
                resp_next.raise_for_status()
                data_next = resp_next.json()
                events = data_next.get('events', [])

        if events:
            now = datetime.now(timezone.utc)
            future_events = []
            for event in events:
                date_str = event.get('dateEvent')
                time_str = event.get('strTime') # Format like "19:00:00" or "19:00:00+XX:XX" or null
                name = event.get('strEvent', f'Unknown {series.capitalize()} Race')
                venue_name = event.get('strVenue', 'Unknown location')

                if not date_str:
                    continue # Skip events without a date

                event_time_utc = None
                try:
                    # Handle different time formats from TheSportsDB
                    if time_str and time_str != "00:00:00":
                        full_dt_str = f"{date_str}T{time_str}"
                        # Check if timezone info is already included
                        if ":" in time_str and ("+" in time_str or "-" in time_str):
                             # Assume ISO 8601 format with timezone offset
                             event_time_utc = datetime.fromisoformat(full_dt_str).astimezone(timezone.utc)
                        else:
                             # Assume time is UTC if no offset provided
                             full_dt_str_utc = f"{full_dt_str}Z"
                             event_time_utc = datetime.fromisoformat(full_dt_str_utc.replace("Z", "+00:00"))
                    else:
                        # If time is missing or "00:00:00", treat it as start of the day UTC
                        event_time_utc = datetime.strptime(date_str, "%Y-%m-%d")
                        event_time_utc = pytz.utc.localize(event_time_utc) # Make it timezone-aware (UTC)

                except ValueError as e:
                    continue # Skip events with unparseable dates/times

                # Compare timezone-aware datetime objects
                if event_time_utc > now:
                    future_events.append((event_time_utc, name, venue_name))

            if future_events:
                future_events.sort(key=lambda x: x[0]) # Find the soonest future event
                next_event_time_utc, next_name, next_venue = future_events[0]

                # Convert to US/Eastern for display
                est = pytz.timezone('US/Eastern')
                event_time_est = next_event_time_utc.astimezone(est)
                # Format date and time clearly
                formatted_date = event_time_est.strftime('%B %d, %Y at %I:%M %p %Z')

                thesportsdb_result = {
                    'name': next_name,
                    'venue': next_venue,
                    'date': formatted_date
                }
            else:
                print(f"No future {series.capitalize()} events found in TheSportsDB schedule for {current_year} or {current_year + 1}.")
        else:
             print(f"No {series.capitalize()} events found in TheSportsDB for season {current_year} or {current_year + 1}.")

    except requests.exceptions.RequestException:
        pass
    except Exception:
        pass

    return thesportsdb_result

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
