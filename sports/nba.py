import os
import requests
import discord
from discord import app_commands
from datetime import datetime, timezone
import pytz

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')
PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')

NBA_TEAMS = {
    'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BKN': 'Brooklyn Nets', 'CHA': 'Charlotte Hornets',
    'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers', 'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets',
    'DET': 'Detroit Pistons', 'GS': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',
    'LAC': 'LA Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies', 'MIA': 'Miami Heat',
    'MIL': 'Milwaukee Bucks', 'MIN': 'Minnesota Timberwolves', 'NO': 'New Orleans Pelicans', 'NY': 'New York Knicks',
    'OKC': 'Oklahoma City Thunder', 'ORL': 'Orlando Magic', 'PHI': 'Philadelphia 76ers', 'PHX': 'Phoenix Suns',
    'POR': 'Portland Trail Blazers', 'SAC': 'Sacramento Kings', 'SA': 'San Antonio Spurs', 'TOR': 'Toronto Raptors',
    'UTA': 'Utah Jazz', 'WAS': 'Washington Wizards'
}

TEAM_NAME_TO_ABBR = {v.lower(): k for k, v in NBA_TEAMS.items()}


def get_nba_games():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    events = resp.json().get('events', [])
    print(f"[DEBUG] get_nba_games: {len(events)} events fetched.")
    if events:
        print(f"[DEBUG] Sample event keys: {list(events[0].keys())}")
    return events


def find_team_abbr(team_query: str):
    team_query = team_query.strip().lower()
    if team_query.upper() in NBA_TEAMS:
        abbr = team_query.upper()
        print(f"[DEBUG] find_team_abbr: direct match for '{team_query}' -> {abbr}")
        return abbr
    if team_query in TEAM_NAME_TO_ABBR:
        abbr = TEAM_NAME_TO_ABBR[team_query]
        print(f"[DEBUG] find_team_abbr: name match for '{team_query}' -> {abbr}")
        return abbr
    # Try partial match
    for abbr, name in NBA_TEAMS.items():
        if team_query in name.lower() or team_query == abbr.lower():
            print(f"[DEBUG] find_team_abbr: partial match for '{team_query}' -> {abbr}")
            return abbr
    print(f"[DEBUG] find_team_abbr: no match for '{team_query}'")
    return None


def get_nba_team_game_info(team_abbr):
    events = get_nba_games()
    now = datetime.now(timezone.utc)
    est = pytz.timezone('US/Eastern')
    print(f"[DEBUG] get_nba_team_game_info: searching for team_abbr={team_abbr}")
    is_playoff_season = False
    # Check if any event is a playoff game to determine playoff season
    for event in events:
        season = event.get('season', {})
        if season.get('type') == 3:
            is_playoff_season = True
            break
    for event in events:
        competitions = event.get('competitions', [])
        if not competitions:
            continue
        comp = competitions[0]
        competitors = comp.get('competitors', [])
        abbrs = [c['team']['abbreviation'] for c in competitors]
        print(f"[DEBUG] Event competitors: {abbrs}")
        teams = {c['team']['abbreviation']: c for c in competitors}
        if team_abbr not in teams:
            continue
        status = comp.get('status', {})
        state = status.get('type', {}).get('state')
        # Check for playoff game
        is_playoff = False
        season = event.get('season', {})
        if season.get('type') == 3:
            is_playoff = True
        playoff_label = " (Playoff Game)" if is_playoff else ""
        if state == 'in':
            lines = []
            for c in competitors:
                name = c['team']['displayName']
                score = c.get('score', '?')
                lines.append(f"{name}: {score}")
            clock = status.get('displayClock', '')
            period = status.get('period', '')
            return f"Current game{playoff_label}:\n" + '\n'.join(lines) + f"\nPeriod: {period}, Clock: {clock}"
        elif state == 'pre':
            date_str = event.get('date')
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            dt_est = dt.astimezone(est)
            opp = [c for c in competitors if c['team']['abbreviation'] != team_abbr][0]
            opp_name = opp['team']['displayName']
            venue = comp.get('venue', {}).get('fullName', 'TBD')
            return f"Next game{playoff_label}: vs {opp_name} at {venue} on {dt_est.strftime('%B %d, %Y at %I:%M %p EST')}"
        elif state == 'post':
            lines = []
            for c in competitors:
                name = c['team']['displayName']
                score = c.get('score', '?')
                lines.append(f"{name}: {score}")
            return f"Last game final score{playoff_label}:\n" + '\n'.join(lines)
    if is_playoff_season:
        return "No current or upcoming games found for that team. It is currently playoff season, so future games may not be scheduled yet."
    return "No current or upcoming games found for that team."


def get_live_nba_games():
    events = get_nba_games()
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
            playoff = event.get('season', {}).get('type') == 3
            clock = status.get('displayClock', '')
            period = status.get('period', '')
            live_games.append({
                'teams': teams,
                'scores': scores,
                'playoff': playoff,
                'clock': clock,
                'period': period
            })
    return live_games


def get_last_nba_games():
    events = get_nba_games()
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
            # NBA Finals detection: Playoff (3) and event name contains 'Finals'
            event_name = event.get('name', '').lower()
            if season_type == '3' and 'finals' in event_name:
                label = 'NBA Finals'
            elif season_type == '3':
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


def add_nba_commands(bot):
    @bot.tree.command(
        name="nba",
        description="Show the current or next NBA game for a team",
        guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None
    )
    @app_commands.describe(team="NBA team name or abbreviation (e.g. Celtics or BOS)")
    async def nba(interaction: discord.Interaction, team: str):
        await interaction.response.defer()
        abbr = find_team_abbr(team)
        if not abbr:
            await interaction.followup.send(f"Unknown team: {team}. Try a full team name or abbreviation.")
            return
        try:
            info = get_nba_team_game_info(abbr)
        except Exception as e:
            info = f"Error fetching NBA info: {e}"
        await interaction.followup.send(info)
    @bot.tree.command(
        name="nba_live",
        description="List all currently live NBA games",
        guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None
    )
    async def nba_live(interaction: discord.Interaction):
        await interaction.response.defer()
        live_games = get_live_nba_games()
        if live_games:
            lines = []
            for g in live_games:
                playoff_label = " [Playoff]" if g['playoff'] else ""
                teams = f"{g['teams'][0]} vs {g['teams'][1]}"
                scores = f"`{g['scores'][0]}` - `{g['scores'][1]}`"
                period = f"P{g['period']}" if g['period'] else ""
                clock = f"{g['clock']}" if g['clock'] else ""
                details = f"{period} {clock}".strip()
                if details:
                    lines.append(f"{teams}: {scores} {details}{playoff_label}")
                else:
                    lines.append(f"{teams}: {scores}{playoff_label}")
            await interaction.followup.send("Live NBA games:\n" + "\n".join(lines))
            return
        # If no live games, show last finished games
        last_games = get_last_nba_games()
        if last_games:
            lines = []
            for g in last_games:
                label = g.get('label', 'Game')
                teams = f"{g['teams'][0]} vs {g['teams'][1]}"
                scores = f"`{g['scores'][0]}` - `{g['scores'][1]}`"
                lines.append(f"{teams}: {scores} [{label}]")
            await interaction.followup.send("No live NBA games. Most recent games:\n" + "\n".join(lines))
        else:
            await interaction.followup.send("No live or recent NBA games found.")
