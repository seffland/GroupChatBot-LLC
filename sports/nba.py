import os
import requests
import discord
from discord import app_commands
import pytz

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')
PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')


def get_nba_games():
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    events = resp.json().get('events', [])
    print(f"[DEBUG] get_nba_games: {len(events)} events fetched.")
    if events:
        print(f"[DEBUG] Sample event keys: {list(events[0].keys())}")
    return events


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
        description="List all currently live NBA games",
        guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None
    )
    async def nba(interaction: discord.Interaction):
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
