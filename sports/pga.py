import os
import requests
import discord
from discord import app_commands

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')

# Fetch PGA events from TheSportsDB
# League ID for PGA: 4425
THESPORTSDB_PGA_ID = "4425"

def get_pga_events():
    import datetime
    current_year = datetime.datetime.now().year
    endpoints = [
        f"https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4425&s={current_year}",
        f"https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=4425&s={current_year-1}",
        f"https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php?id=4425",
        f"https://www.thesportsdb.com/api/v1/json/3/eventspastleague.php?id=4425"
    ]
    all_events = []
    for url in endpoints:
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            events = data.get('events', [])
            for event in events:
                sport = event.get('strSport', '').lower()
                name = event.get('strEvent', '').lower()
                if sport == 'golf' or any(word in name for word in ['open', 'championship', 'masters', 'classic', 'invitational', 'pga', 'memorial', 'cup']):
                    all_events.append(event)
        except Exception as e:
            continue
    return all_events

# Get live PGA tournaments (in progress)
def get_live_pga_tournaments():
    import datetime
    now = datetime.datetime.utcnow()
    events = get_pga_events()
    live_tournaments = []
    for event in events:
        date_str = event.get('dateEvent')
        time_str = event.get('strTime')
        if not date_str:
            continue
        try:
            if time_str and time_str != "00:00:00":
                dt = datetime.datetime.fromisoformat(f"{date_str}T{time_str}")
            else:
                dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            continue
        # Consider a tournament 'live' if today is within the event date
        if dt.date() == now.date():
            name = event.get('strEvent', 'Unknown Tournament')
            venue = event.get('strVenue', 'Unknown venue')
            status = event.get('strStatus', '')
            live_tournaments.append({
                'name': name,
                'venue': venue,
                'status': status
            })
    return live_tournaments

# Get most recent finished PGA tournaments
def get_last_pga_tournaments():
    import datetime
    now = datetime.datetime.utcnow()
    events = get_pga_events()
    finished_tournaments = []
    for event in events:
        date_str = event.get('dateEvent')
        if not date_str:
            continue
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            continue
        if dt < now:
            name = event.get('strEvent', 'Unknown Tournament')
            venue = event.get('strVenue', 'Unknown venue')
            status = event.get('strStatus', '')
            str_result = event.get('strResult', '')
            description = event.get('strDescriptionEN', '')
            leaderboard = []
            if str_result:
                import re
                lines = [line for line in str_result.split('\n') if line.strip()]
                found = False
                for line in lines:
                    if re.match(r"^(T?\d+|[1-5])\s+", line):
                        found = True
                        leaderboard.append(line.strip())
                    elif found and len(leaderboard) < 5:
                        leaderboard.append(line.strip())
                    if len(leaderboard) >= 5:
                        break
                if not leaderboard and len(lines) > 2:
                    leaderboard = lines[2:7]
            finished_tournaments.append({
                'name': name,
                'venue': venue,
                'status': status,
                'date': date_str,
                'leaderboard': leaderboard,
                'description': description
            })
    finished_tournaments.sort(key=lambda x: x['date'], reverse=True)
    return finished_tournaments[:1]

def get_next_pga_tournament():
    import datetime
    now = datetime.datetime.utcnow()
    events = get_pga_events()
    future_tournaments = []
    for event in events:
        date_str = event.get('dateEvent')
        if not date_str:
            continue
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            continue
        if dt > now:
            name = event.get('strEvent', 'Unknown Tournament')
            venue = event.get('strVenue', 'Unknown venue')
            status = event.get('strStatus', '')
            future_tournaments.append({
                'name': name,
                'venue': venue,
                'status': status,
                'date': date_str
            })
    future_tournaments.sort(key=lambda x: x['date'])
    return future_tournaments[0] if future_tournaments else None

# For Discord integration
def add_pga_commands(bot):
    @bot.tree.command(
        name="pga",
        description="List all currently live PGA tournaments"
        # No guild restriction, available globally
    )
    async def pga(interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            live_tournaments = get_live_pga_tournaments()
        except Exception:
            live_tournaments = []
        if live_tournaments:
            lines = []
            for t in live_tournaments:
                name = t['name']
                venue = t.get('venue', '')
                status = t.get('status', '')
                lines.append(f"**{name}** at {venue}\n{status}")
            await interaction.followup.send("Live PGA tournaments:\n" + "\n".join(lines))
            return
        try:
            last_tournaments = get_last_pga_tournaments()
        except Exception:
            last_tournaments = []
        try:
            next_tournament = get_next_pga_tournament()
        except Exception:
            next_tournament = None
        lines = []
        if last_tournaments:
            t = last_tournaments[0]
            name = t['name']
            venue = t.get('venue', '')
            status = t.get('status', '')
            date = t.get('date', '')
            # Format date as MM/DD/YYYY
            try:
                from datetime import datetime
                date_fmt = datetime.strptime(date, "%Y-%m-%d").strftime("%m/%d/%Y")
            except Exception:
                date_fmt = date
            leaderboard = t.get('leaderboard', [])
            if leaderboard:
                leaderboard_str = '\n'.join(leaderboard)
                lines.append(f"**{name}** at {venue} on {date_fmt}\n{status}\nTop finishers:\n{leaderboard_str}")
            else:
                lines.append(f"**{name}** at {venue} on {date_fmt}\n{status}")
        if next_tournament:
            n = next_tournament
            ndate = n['date']
            # Format date as MM/DD/YYYY
            try:
                from datetime import datetime
                ndate_fmt = datetime.strptime(ndate, "%Y-%m-%d").strftime("%m/%d/%Y")
            except Exception:
                ndate_fmt = ndate
            lines.append(f"Next tournament: **{n['name']}** at {n['venue']} on {ndate_fmt}")
        if lines:
            await interaction.followup.send("No live PGA tournaments. Most recent:\n" + " ".join(lines))
        else:
            await interaction.followup.send("No live or recent PGA tournaments found.")
