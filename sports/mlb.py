import os
import requests
import discord
from discord import app_commands

DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')

def get_mlb_games():
    url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    events = resp.json().get('events', [])
    return events

def get_live_mlb_games():
    events = get_mlb_games()
    live_games = []
    for event in events:
        competitions = event.get('competitions', [])
        for comp in competitions:  # Iterate over all competitions for doubleheaders
            status = comp.get('status', {})
            state = status.get('type', {}).get('state')
            if state == 'in':
                short_detail = status.get('type', {}).get('shortDetail', '')
                competitors = comp.get('competitors', [])
                teams = [c['team']['displayName'] for c in competitors]
                scores = [c.get('score', '?') for c in competitors]
                live_games.append({
                    'teams': teams,
                    'scores': scores,
                    'inning_status': short_detail
                })
    return live_games

def get_last_mlb_games():
    events = get_mlb_games()
    finished_games = []
    for event in events:
        competitions = event.get('competitions', [])
        for comp in competitions:  # Iterate over all competitions for doubleheaders
            status = comp.get('status', {})
            state = status.get('type', {}).get('state')
            if state == 'post':
                competitors = comp.get('competitors', [])
                teams = [c['team']['displayName'] for c in competitors]
                scores = [c.get('score', '?') for c in competitors]
                season_type = str(event.get('season', {}).get('type'))
                event_name = event.get('name', '').lower()
                if season_type == '3' and 'world series' in event_name:
                    label = 'World Series'
                elif season_type == '3':
                    label = 'Postseason'
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

def add_mlb_commands(bot):
    @bot.tree.command(
        name="mlb",
        description="List all currently live MLB games",
        #guild=discord.Object(id=int(DEVELOPMENT_SERVER_ID)) if DEVELOPMENT_SERVER_ID else None
    )
    async def mlb(interaction: discord.Interaction):
        await interaction.response.defer()
        live_games = get_live_mlb_games()
        if live_games:
            lines = []
            for g in live_games:
                teams = f"{g['teams'][0]} vs {g['teams'][1]}"
                scores = f"`{g['scores'][0]}` - `{g['scores'][1]}`"
                inning_status = g.get('inning_status', '')
                inning_str = inning_status if inning_status else ''
                lines.append(f"{teams}: {scores} [{inning_str}]")
            await interaction.followup.send("Live MLB games:\n" + "\n".join(lines))
            return
        last_games = get_last_mlb_games()
        if last_games:
            lines = []
            for g in last_games:
                label = g.get('label', 'Game')
                teams = f"{g['teams'][0]} vs {g['teams'][1]}"
                scores = f"`{g['scores'][0]}` - `{g['scores'][1]}`"
                lines.append(f"{teams}: {scores} [{label}]")
            await interaction.followup.send("No live MLB games. Most recent games:\n" + "\n".join(lines))
        else:
            await interaction.followup.send("No live or recent MLB games found.")
