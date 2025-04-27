import os
import requests
import discord
from discord import app_commands
import pytz

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')
PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')

def get_nfl_games():
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    events = resp.json().get('events', [])
    return events

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
            if season_type in ['3', '5']:
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
        description="List all currently live NFL games",
        guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None
    )
    async def nfl(interaction: discord.Interaction):
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
            await interaction.followup.send("No live NFL games. Most recent game(s):\n" + "\n".join(lines))
        else:
            await interaction.followup.send("No live or recent NFL games found.")
