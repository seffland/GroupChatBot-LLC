import os
import requests
import discord
from discord import app_commands
from datetime import datetime, timezone
import pytz

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')
PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')

MLB_TEAMS = {
    'ARI': 'Arizona Diamondbacks', 'ATL': 'Atlanta Braves', 'BAL': 'Baltimore Orioles', 'BOS': 'Boston Red Sox',
    'CHC': 'Chicago Cubs', 'CWS': 'Chicago White Sox', 'CIN': 'Cincinnati Reds', 'CLE': 'Cleveland Guardians',
    'COL': 'Colorado Rockies', 'DET': 'Detroit Tigers', 'HOU': 'Houston Astros', 'KC': 'Kansas City Royals',
    'LAA': 'Los Angeles Angels', 'LAD': 'Los Angeles Dodgers', 'MIA': 'Miami Marlins', 'MIL': 'Milwaukee Brewers',
    'MIN': 'Minnesota Twins', 'NYM': 'New York Mets', 'NYY': 'New York Yankees', 'OAK': 'Oakland Athletics',
    'PHI': 'Philadelphia Phillies', 'PIT': 'Pittsburgh Pirates', 'SD': 'San Diego Padres', 'SF': 'San Francisco Giants',
    'SEA': 'Seattle Mariners', 'STL': 'St. Louis Cardinals', 'TB': 'Tampa Bay Rays', 'TEX': 'Texas Rangers',
    'TOR': 'Toronto Blue Jays', 'WSH': 'Washington Nationals'
}

TEAM_NAME_TO_ABBR = {v.lower(): k for k, v in MLB_TEAMS.items()}

def get_mlb_games():
    url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    events = resp.json().get('events', [])
    return events

def find_team_abbr(team_query: str):
    team_query = team_query.strip().lower()
    if team_query.upper() in MLB_TEAMS:
        return team_query.upper()
    if team_query in TEAM_NAME_TO_ABBR:
        return TEAM_NAME_TO_ABBR[team_query]
    for abbr, name in MLB_TEAMS.items():
        if team_query in name.lower() or team_query == abbr.lower():
            return abbr
    return None

def get_mlb_team_game_info(team_abbr):
    events = get_mlb_games()
    est = pytz.timezone('US/Eastern')
    for event in events:
        competitions = event.get('competitions', [])
        if not competitions:
            continue
        comp = competitions[0]
        competitors = comp.get('competitors', [])
        abbrs = [c['team']['abbreviation'] for c in competitors]
        teams = {c['team']['abbreviation']: c for c in competitors}
        if team_abbr not in teams:
            continue
        status = comp.get('status', {})
        state = status.get('type', {}).get('state')
        if state == 'in':
            lines = []
            for c in competitors:
                name = c['team']['displayName']
                score = c.get('score', '?')
                lines.append(f"{name}: {score}")
            inning = status.get('period', '')
            clock = status.get('displayClock', '')
            return f"Current game:\n" + '\n'.join(lines) + f"\nInning: {inning}, {clock}"
        elif state == 'pre':
            date_str = event.get('date')
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            dt_est = dt.astimezone(est)
            opp = [c for c in competitors if c['team']['abbreviation'] != team_abbr][0]
            opp_name = opp['team']['displayName']
            venue = comp.get('venue', {}).get('fullName', 'TBD')
            return f"Next game: vs {opp_name} at {venue} on {dt_est.strftime('%B %d, %Y at %I:%M %p EST')}"
        elif state == 'post':
            lines = []
            for c in competitors:
                name = c['team']['displayName']
                score = c.get('score', '?')
                lines.append(f"{name}: {score}")
            return f"Last game final score:\n" + '\n'.join(lines)
    return "No current or upcoming games found for that team."

def get_live_mlb_games():
    events = get_mlb_games()
    live_games = []
    for event in events:
        competitions = event.get('competitions', [])
        if not competitions:
            continue
        comp = competitions[0]
        status = comp.get('status', {})
        state = status.get('type', {}).get('state')
        if state == 'in':
            competitors = comp.get('competitors', [])
            teams = [c['team']['displayName'] for c in competitors]
            scores = [c.get('score', '?') for c in competitors]
            inning = status.get('period', '')
            clock = status.get('displayClock', '')
            live_games.append({
                'teams': teams,
                'scores': scores,
                'inning': inning,
                'clock': clock
            })
    return live_games

def get_last_mlb_games():
    events = get_mlb_games()
    finished_games = []
    for event in events:
        competitions = event.get('competitions', [])
        if not competitions:
            continue
        comp = competitions[0]
        status = comp.get('status', {})
        state = status.get('type', {}).get('state')
        if state == 'post':
            competitors = comp.get('competitors', [])
            teams = [c['team']['displayName'] for c in competitors]
            scores = [c.get('score', '?') for c in competitors]
            finished_games.append({
                'teams': teams,
                'scores': scores
            })
    return finished_games

def add_mlb_command(bot):
    @bot.tree.command(
        name="mlb",
        description="Show the current or next MLB game for a team",
        guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None
    )
    @app_commands.describe(team="MLB team name or abbreviation (e.g. Yankees or NYY)")
    async def mlb(interaction: discord.Interaction, team: str):
        await interaction.response.defer()
        abbr = find_team_abbr(team)
        if not abbr:
            await interaction.followup.send(f"Unknown team: {team}. Try a full team name or abbreviation.")
            return
        try:
            info = get_mlb_team_game_info(abbr)
        except Exception as e:
            info = f"Error fetching MLB info: {e}"
        await interaction.followup.send(info)
    @bot.tree.command(
        name="mlb_live",
        description="List all currently live MLB games",
        guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None
    )
    async def mlb_live(interaction: discord.Interaction):
        await interaction.response.defer()
        live_games = get_live_mlb_games()
        if live_games:
            lines = []
            for g in live_games:
                teams = f"{g['teams'][0]} vs {g['teams'][1]}"
                scores = f"`{g['scores'][0]}` - `{g['scores'][1]}`"
                lines.append(f"{teams}: {scores}")
            await interaction.followup.send("Live MLB games:\n" + "\n".join(lines))
            return
        # If no live games, show last finished games
        last_games = get_last_mlb_games()
        if last_games:
            lines = []
            for g in last_games:
                teams = f"{g['teams'][0]} vs {g['teams'][1]}"
                scores = f"`{g['scores'][0]}` - `{g['scores'][1]}`"
                lines.append(f"{teams}: {scores}")
            await interaction.followup.send("No live MLB games. Most recent finals:\n" + "\n".join(lines))
        else:
            await interaction.followup.send("No live or recent MLB games found.")
