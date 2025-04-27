import os
import requests
import discord
from discord import app_commands
from datetime import datetime, timezone
import pytz

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')
PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')

NFL_TEAMS = {
    'ARI': 'Arizona Cardinals', 'ATL': 'Atlanta Falcons', 'BAL': 'Baltimore Ravens', 'BUF': 'Buffalo Bills',
    'CAR': 'Carolina Panthers', 'CHI': 'Chicago Bears', 'CIN': 'Cincinnati Bengals', 'CLE': 'Cleveland Browns',
    'DAL': 'Dallas Cowboys', 'DEN': 'Denver Broncos', 'DET': 'Detroit Lions', 'GB': 'Green Bay Packers',
    'HOU': 'Houston Texans', 'IND': 'Indianapolis Colts', 'JAX': 'Jacksonville Jaguars', 'KC': 'Kansas City Chiefs',
    'LV': 'Las Vegas Raiders', 'LAC': 'Los Angeles Chargers', 'LAR': 'Los Angeles Rams', 'MIA': 'Miami Dolphins',
    'MIN': 'Minnesota Vikings', 'NE': 'New England Patriots', 'NO': 'New Orleans Saints', 'NYG': 'New York Giants',
    'NYJ': 'New York Jets', 'PHI': 'Philadelphia Eagles', 'PIT': 'Pittsburgh Steelers', 'SF': 'San Francisco 49ers',
    'SEA': 'Seattle Seahawks', 'TB': 'Tampa Bay Buccaneers', 'TEN': 'Tennessee Titans', 'WAS': 'Washington Commanders'
}

TEAM_NAME_TO_ABBR = {v.lower(): k for k, v in NFL_TEAMS.items()}

def get_nfl_games():
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    events = resp.json().get('events', [])
    return events

def find_team_abbr(team_query: str):
    team_query = team_query.strip().lower()
    if team_query.upper() in NFL_TEAMS:
        return team_query.upper()
    if team_query in TEAM_NAME_TO_ABBR:
        return TEAM_NAME_TO_ABBR[team_query]
    for abbr, name in NFL_TEAMS.items():
        if team_query in name.lower() or team_query == abbr.lower():
            return abbr
    return None

def get_nfl_team_game_info(team_abbr):
    events = get_nfl_games()
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
        # Check for Super Bowl by season type
        season = event.get('season', {})
        is_super_bowl = str(season.get('type')) == '5'
        if state == 'in':
            lines = []
            for c in competitors:
                name = c['team']['displayName']
                score = c.get('score', '?')
                lines.append(f"{name}: {score}")
            quarter = status.get('period', '')
            clock = status.get('displayClock', '')
            label = " (Super Bowl)" if is_super_bowl else ""
            return f"Current game{label}:\n" + '\n'.join(lines) + f"\nQuarter: {quarter}, {clock}"
        elif state == 'pre':
            date_str = event.get('date')
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            dt_est = dt.astimezone(est)
            opp = [c for c in competitors if c['team']['abbreviation'] != team_abbr][0]
            opp_name = opp['team']['displayName']
            venue = comp.get('venue', {}).get('fullName', 'TBD')
            label = " (Super Bowl)" if is_super_bowl else ""
            return f"Next game{label}: vs {opp_name} at {venue} on {dt_est.strftime('%B %d, %Y at %I:%M %p EST')}"
        elif state == 'post':
            lines = []
            for c in competitors:
                name = c['team']['displayName']
                score = c.get('score', '?')
                lines.append(f"{name}: {score}")
            label = " (Super Bowl)" if is_super_bowl else ""
            return f"Last game final score{label}:\n" + '\n'.join(lines)
    return "No current or upcoming games found for that team."

def get_live_nfl_games():
    events = get_nfl_games()
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
            quarter = status.get('period', '')
            clock = status.get('displayClock', '')
            live_games.append({
                'teams': teams,
                'scores': scores,
                'quarter': quarter,
                'clock': clock
            })
    return live_games

def get_last_nfl_games():
    events = get_nfl_games()
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
            season_type = str(event.get('season', {}).get('type'))
            # Debug print for season type and teams
            print(f"DEBUG: season_type={season_type}, teams={teams}")
            if season_type == '5':
                label = 'Super Bowl'
            elif season_type == '4':
                label = 'Playoff'
            elif season_type == '2':
                label = 'Regular Season'
            elif season_type == '1':
                label = 'Preseason'
            else:
                label = 'Game'
            finished_games.append({
                'teams': teams,
                'scores': scores,
                'label': label
            })
    return finished_games

def add_nfl_commands(bot):
    @bot.tree.command(
        name="nfl",
        description="Show the current or next NFL game for a team",
        guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None
    )
    @app_commands.describe(team="NFL team name or abbreviation (e.g. Eagles or PHI)")
    async def nfl(interaction: discord.Interaction, team: str):
        await interaction.response.defer()
        abbr = find_team_abbr(team)
        if not abbr:
            await interaction.followup.send(f"Unknown team: {team}. Try a full team name or abbreviation.")
            return
        try:
            info = get_nfl_team_game_info(abbr)
        except Exception as e:
            info = f"Error fetching NFL info: {e}"
        await interaction.followup.send(info)
    @bot.tree.command(
        name="nfl_live",
        description="List all currently live NFL games",
        guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None
    )
    async def nfl_live(interaction: discord.Interaction):
        await interaction.response.defer()
        live_games = get_live_nfl_games()
        if live_games:
            lines = []
            for g in live_games:
                teams = f"{g['teams'][0]} vs {g['teams'][1]}"
                scores = f"`{g['scores'][0]}` - `{g['scores'][1]}`"
                quarter = f"Q{g['quarter']}" if g['quarter'] else ""
                clock = f"{g['clock']}" if g['clock'] else ""
                details = f"{quarter} {clock}".strip()
                if details:
                    lines.append(f"{teams}: {scores} {details}")
                else:
                    lines.append(f"{teams}: {scores}")
            await interaction.followup.send("Live NFL games:\n" + "\n".join(lines))
            return
        # If no live games, show last finished games
        last_games = get_last_nfl_games()
        if last_games:
            lines = []
            for g in last_games:
                teams = f"{g['teams'][0]} vs {g['teams'][1]}"
                scores = f"`{g['scores'][0]}` - `{g['scores'][1]}`"
                label = g.get('label', 'Game')
                lines.append(f"{teams}: {scores} [{label}]")
            await interaction.followup.send("No live NFL games. Most recent games:\n" + "\n".join(lines))
        else:
            await interaction.followup.send("No live or recent NFL games found.")
