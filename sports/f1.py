import os
import requests
import discord
from discord import app_commands

PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')
DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')

async def get_next_f1_race():
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
        for race in races:
            event_types = [
                ('FirstPractice', 'Practice 1'),
                ('SecondPractice', 'Practice 2'),
                ('ThirdPractice', 'Practice 3'),
                ('Sprint', 'Sprint'),
                ('SprintQualifying', 'Sprint Qualifying'),
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
            event_time_str = event_time_est.strftime("%m/%d/%Y at %I:%M %p EST")
            msg += f"The next F1 event is **{next_event_type}** at **{event_loc_str}** on **{event_time_str}**.\n"
        if next_race:
            race_name = next_race.get('raceName', 'Unknown')
            race_circuit = next_race.get('Circuit', {})
            race_loc = race_circuit.get('circuitName', 'Unknown location')
            race_city = race_circuit.get('Location', {}).get('locality', '')
            race_country = race_circuit.get('Location', {}).get('country', '')
            race_loc_str = f"{race_loc} ({race_city}, {race_country})" if race_city or race_country else race_loc
            race_time_est = next_race_time.astimezone(est)
            race_time_str = race_time_est.strftime("%m/%d/%Y at %I:%M %p EST")
            msg += f"The next F1 race is **{race_name}** at **{race_loc_str}** on **{race_time_str}**."
        return msg.strip()
    except Exception as e:
        return f"Could not fetch F1 event info: {e}"

async def get_last_f1_race_winner():
    """
    Fetch the most recent completed F1 race and return the winner's name, race name, date, and location.
    Tries TheSportsDB for results, falls back to Ergast if needed.
    Returns None if not found or on error.
    """
    import datetime
    import pytz
    import requests
    import re
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    current_year = now.year
    # 1. Try TheSportsDB
    try:
        # Get all F1 events for the current season
        events_url = f"https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4370&s={current_year}"
        resp = requests.get(events_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        events = data.get('events', [])
        # Find the most recent event before now with a valid event id
        past_events = []
        for event in events:
            date_str = event.get('dateEvent')
            if not date_str or not event.get('idEvent'):
                continue
            try:
                event_time = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                event_time = pytz.utc.localize(event_time)
            except Exception:
                continue
            if event_time < now:
                past_events.append((event_time, event))
        if past_events:
            past_events.sort(key=lambda x: x[0], reverse=True)
            last_event_time, last_event = past_events[0]
            race_name = last_event.get('strEvent', 'Unknown race')
            location = last_event.get('strVenue', 'Unknown location')
            date = last_event.get('dateEvent')
            str_result = last_event.get('strResult', '')
            # Try to extract winner from strResult
            winner = None
            if str_result:
                # Look for: The race was won by <Name> (in the ...)
                m = re.search(r"The race was won by ([A-Za-z .'-]+) in the", str_result)
                if m:
                    winner = m.group(1).strip()
            if winner:
                return {
                    'winner': winner,
                    'race': race_name,
                    'date': date,
                    'location': location
                }
    except Exception:
        pass
    # 2. Fallback to Ergast
    def fetch_races_for_season(season):
        url = f"https://ergast.com/api/f1/{season}/results.json"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data['MRData']['RaceTable']['Races']
    try:
        races = fetch_races_for_season(current_year)
        past_races = []
        for race in races:
            race_date = race.get('date')
            race_time = race.get('time', '00:00:00')
            dt_utc = datetime.datetime.strptime(race_date + ' ' + race_time.replace('Z', ''), "%Y-%m-%d %H:%M:%S")
            dt_utc = dt_utc.replace(tzinfo=datetime.timezone.utc)
            if dt_utc < now and race.get('Results'):
                past_races.append((dt_utc, race))
        if not past_races:
            races = fetch_races_for_season(current_year - 1)
            for race in races:
                race_date = race.get('date')
                race_time = race.get('time', '00:00:00')
                dt_utc = datetime.datetime.strptime(race_date + ' ' + race_time.replace('Z', ''), "%Y-%m-%d %H:%M:%S")
                dt_utc = dt_utc.replace(tzinfo=datetime.timezone.utc)
                if dt_utc < now and race.get('Results'):
                    past_races.append((dt_utc, race))
        if not past_races:
            return None
        past_races.sort(key=lambda x: x[0], reverse=True)
        last_race_time, last_race = past_races[0]
        race_name = last_race.get('raceName', 'Unknown race')
        circuit = last_race.get('Circuit', {})
        location = circuit.get('circuitName', 'Unknown location')
        city = circuit.get('Location', {}).get('locality', '')
        country = circuit.get('Location', {}).get('country', '')
        loc_str = f"{location} ({city}, {country})" if city or country else location
        winner = 'Unknown'
        if last_race.get('Results'):
            winner = last_race['Results'][0]['Driver']['familyName']
            given = last_race['Results'][0]['Driver']['givenName']
            winner = f"{given} {winner}"
        date = last_race.get('date')
        return {
            'winner': winner,
            'race': race_name,
            'date': date,
            'location': loc_str
        }
    except Exception:
        return None

def add_f1_command(bot):
    @bot.tree.command(name="f1", description="Show the location and time of the next F1 race")
    async def f1(interaction: discord.Interaction):
        await interaction.response.defer()
        info = await get_next_f1_race()
        await interaction.followup.send(info)

    @bot.tree.command(
        name="f1_winner",
        description="Show the winner of the most recent F1 race (dev only)",
        guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None
    )
    async def f1_winner(interaction: discord.Interaction):
        await interaction.response.defer()
        result = await get_last_f1_race_winner()
        if result:
            await interaction.followup.send(f"{result['winner']} won the {result['race']} at {result['location']} on {result['date']}.")
        else:
            await interaction.followup.send("Could not fetch the last F1 race winner.")

    @bot.tree.command(
        name="f1_winners",
        description="Show all F1 race winners for the current year (dev only)",
        guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None
    )
    async def f1_winners(interaction: discord.Interaction):
        import datetime
        import pytz
        import requests
        await interaction.response.defer()
        now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        current_year = now.year
        try:
            events_url = f"https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4370&s={current_year}"
            resp = requests.get(events_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            events = data.get('events', [])
            winners = []
            debug_lines = []
            for event in events:
                date_str = event.get('dateEvent')
                id_event = event.get('idEvent')
                race_name = event.get('strEvent', 'Unknown race')
                if not date_str or not id_event:
                    continue
                name_lower = race_name.lower()
                if (
                    'grand prix' not in name_lower or
                    'practice' in name_lower or
                    'qualifying' in name_lower or
                    'sprint' in name_lower
                ):
                    continue  # Only include main Grand Prix race events
                try:
                    event_time = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                    event_time = pytz.utc.localize(event_time)
                except Exception:
                    continue
                location = event.get('strVenue', 'Unknown location')
                date = event.get('dateEvent')
                winner = None
                debug_info = f"idEvent: {id_event}, url: https://www.thesportsdb.com/api/v1/json/3/eventresults.php?id={id_event}\n"
                try:
                    results_url = f"https://www.thesportsdb.com/api/v1/json/3/eventresults.php?id={id_event}"
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                    results_resp = requests.get(results_url, headers=headers, timeout=10)
                    results_resp.raise_for_status()
                    results_data = results_resp.json()
                    results = results_data.get('results', [])
                    if not results:
                        print(f"RAW RESPONSE for idEvent {id_event}: {results_resp.text}")
                    debug_info += f"results: {results[:2]}\n"
                    if results and isinstance(results, list):
                        for r in results:
                            pos = r.get('intPosition')
                            if pos == 1 or str(pos) == '1':
                                winner = r.get('strPlayer')
                                break
                except Exception as e:
                    debug_info += f"Exception: {e}\n"
                if winner:
                    winners.append({
                        'race': race_name,
                        'date': date,
                        'location': location,
                        'winner': winner,
                        'id_event': id_event
                    })
                print(debug_info)  # Print debug info to console for dev
            real_winners = [w for w in winners if w['winner']]
            if real_winners:
                lines = [f"{w['date']}: {w['winner']} won the {w['race']} at {w['location']}" for w in real_winners]
                output = '\n'.join(lines)
                if len(output) > 1900:
                    output = output[:1900] + "..."
                await interaction.followup.send(f"**F1 race winners for {current_year}:**\n" + output)
            else:
                await interaction.followup.send("No completed F1 races with known winners found for this year.")
        except Exception as e:
            await interaction.followup.send(f"Error fetching F1 winners: {e}")
