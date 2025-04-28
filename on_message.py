import os
import re
import requests
from sports.nba import get_last_nba_games
from sports.mlb import get_last_mlb_games
from sports.nfl import get_last_nfl_games
from sports.nascar import get_last_nascar_cup_winner
from sports.f1 import get_last_f1_race_winner
from ollama_client import ask_ollama
from db import add_message, get_history

def setup_on_message(bot, HISTORY_LIMIT):
    @bot.event
    async def on_message(message):
        if message.author.bot:
            return
        # Listen for $TICKER in messages and reply with stock price (now global)
        # Match $ followed by 1-5 uppercase letters, ensuring it's a whole word
        match = re.search(r'\$([A-Z]{1,5})\b', message.content)
        if match:
            ticker = match.group(1)
            try:
                finnhub_api_key = os.getenv('FINNHUB_API_KEY')
                if not finnhub_api_key:
                    await message.reply("Finnhub API key not set.")
                    return
                url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={finnhub_api_key}"
                resp = requests.get(url, timeout=10)
                data = resp.json()
                if 'c' in data and data['c']:
                    price = data['c']
                    await message.reply(f"${ticker}: ${price}")
                else:
                    await message.reply(f"Could not fetch price for ${ticker}.")
            except Exception as e:
                await message.reply(f"Error fetching price for ${ticker}: {e}")
        # If the bot is mentioned, treat as a chat request
        if bot.user in message.mentions:
            channel_id = message.channel.id
            # Remove the mention from the message content
            content = message.content.replace(f'<@{bot.user.id}>', '').strip()
            content = content.lower().strip()
            # --- SPORTS DETECTION ---
            sports_keywords = [
                'nba', 'mlb', 'nfl', 'basketball', 'baseball', 'football', 'f1', 'nascar',
                # NBA teams
                'warriors', 'lakers', 'celtics', 'bucks', 'suns', 'knicks', 'nets', 'heat', 'bulls', 'mavericks', 'clippers', 'spurs', 'rockets', 'raptors', 'hawks', 'nuggets', '76ers', 'pelicans', 'jazz', 'thunder', 'timberwolves', 'pistons', 'magic', 'kings', 'wizards', 'grizzlies', 'hornets', 'pacers', 'cavaliers', 'blazers',
                # MLB teams
                'yankees', 'red sox', 'dodgers', 'giants', 'cubs', 'mets', 'braves', 'astros', 'cardinals', 'phillies', 'padres', 'brewers', 'rays', 'blue jays', 'white sox', 'guardians', 'twins', 'mariners', 'angels', 'diamondbacks', 'orioles', 'pirates', 'royals', 'athletics', 'rockies', 'nationals', 'reds', 'rangers', 'tigers', 'marlins',
                # NFL teams
                'patriots', 'chiefs', 'packers', 'steelers', 'cowboys', '49ers', 'giants', 'jets', 'bears', 'eagles', 'dolphins', 'ravens', 'bills', 'browns', 'colts', 'jaguars', 'texans', 'titans', 'broncos', 'chargers', 'raiders', 'bengals', 'saints', 'panthers', 'buccaneers', 'falcons', 'seahawks', 'rams', 'vikings', 'commanders', 'cardinals', 'lions',
            ]
            if any(kw in content for kw in sports_keywords):
                def team_mentioned(team_name, msg):
                    team_words = team_name.lower().replace('state', '').replace('fc', '').replace('sc', '').split()
                    msg = msg.lower()
                    return any(word for word in team_words if len(word) > 2 and word in msg)
                # MLB scores summary if no team mentioned
                if 'mlb' in content and not any(team_mentioned(team, content) for g in get_last_mlb_games() for team in g['teams']):
                    mlb_games = get_last_mlb_games()
                    if mlb_games:
                        summary = '\n'.join([f"{g['teams'][0]} {g['scores'][0]} - {g['teams'][1]} {g['scores'][1]} [{g.get('label','Game')}]" for g in mlb_games])
                        llm_prompt = [
                            {"role": "system", "content": "You are a helpful sports assistant."},
                            {"role": "user", "content": f"Here are all the MLB scores from yesterday (or the most recent day with games):\n{summary}\nPlease answer the user's question in a short, concise way (2-3 sentences or a simple list). The user's question: {content}"}
                        ]
                        response = ask_ollama(llm_prompt, os.getenv('OLLAMA_URL', 'http://plexllm-ollama-1:11434'))
                        await message.reply(response)
                        return
                # NBA scores summary if no team mentioned
                if 'nba' in content and not any(team_mentioned(team, content) for g in get_last_nba_games() for team in g['teams']):
                    nba_games = get_last_nba_games()
                    if nba_games:
                        summary = '\n'.join([f"{g['teams'][0]} {g['scores'][0]} - {g['teams'][1]} {g['scores'][1]} [{g.get('label','Game')}]" for g in nba_games])
                        llm_prompt = [
                            {"role": "system", "content": "You are a helpful sports assistant."},
                            {"role": "user", "content": f"Here are all the NBA scores from yesterday (or the most recent day with games):\n{summary}\nPlease answer the user's question in a short, concise way (2-3 sentences or a simple list). The user's question: {content}"}
                        ]
                        response = ask_ollama(llm_prompt, os.getenv('OLLAMA_URL', 'http://plexllm-ollama-1:11434'))
                        await message.reply(response)
                        return
                # NFL scores summary if no team mentioned
                if 'nfl' in content and not any(team_mentioned(team, content) for g in get_last_nfl_games() for team in g['teams']):
                    nfl_games = get_last_nfl_games()
                    if nfl_games:
                        summary = '\n'.join([f"{g['teams'][0]} {g['scores'][0]} - {g['teams'][1]} {g['scores'][1]} [{g.get('label','Game')}]" for g in nfl_games])
                        llm_prompt = [
                            {"role": "system", "content": "You are a helpful sports assistant."},
                            {"role": "user", "content": f"Here are all the NFL scores from yesterday (or the most recent day with games):\n{summary}\nPlease answer the user's question in a short, concise way (2-3 sentences or a simple list). The user's question: {content}"}
                        ]
                        response = ask_ollama(llm_prompt, os.getenv('OLLAMA_URL', 'http://plexllm-ollama-1:11434'))
                        await message.reply(response)
                        return
                # More robust NASCAR Cup winner detection
                nascar_trigger = (
                    'nascar' in content and
                    (('winner' in content or 'won' in content) and ('race' in content or 'cup' in content))
                )
                f1_trigger = (
                    'f1' in content and
                    ('winner' in content or 'won' in content)
                )
                if nascar_trigger:
                    cup_result = get_last_nascar_cup_winner()
                    if cup_result:
                        summary = f"{cup_result['winner']} won the {cup_result['race']} at {cup_result['location']} on {cup_result['date']}."
                        llm_prompt = [
                            {"role": "system", "content": "You are a helpful sports assistant. Only repeat the summary provided, do not add extra information or disclaimers."},
                            {"role": "user", "content": f"Here is the result of the most recent NASCAR Cup race: {summary}\nPlease answer the user's question by repeating the summary exactly. The user's question: {content}"}
                        ]
                        response = ask_ollama(llm_prompt, os.getenv('OLLAMA_URL', 'http://plexllm-ollama-1:11434'))
                        await message.reply(response)
                        return
                if f1_trigger:
                    f1_result = await get_last_f1_race_winner()
                    if f1_result:
                        summary = f"{f1_result['winner']} won the {f1_result['race']} at {f1_result['location']} on {f1_result['date']}."
                        llm_prompt = [
                            {"role": "system", "content": "You are a helpful sports assistant. Only repeat the summary provided, do not add extra information or disclaimers."},
                            {"role": "user", "content": f"Here is the result of the most recent F1 race: {summary}\nPlease answer the user's question by repeating the summary exactly. The user's question: {content}"}
                        ]
                        response = ask_ollama(llm_prompt, os.getenv('OLLAMA_URL', 'http://plexllm-ollama-1:11434'))
                        await message.reply(response)
                        return
                # ...existing team-specific logic...
            # --- END SPORTS DETECTION ---
            add_message(channel_id, "user", message.author.name, content)
            SHORT_HISTORY_LIMIT = 8
            history = get_history(channel_id, SHORT_HISTORY_LIMIT)
            llm_prompt = [
                {"role": "system", "content": "You are a helpful assistant. Answer the user's request directly and concisely. Do not summarize previous conversation unless asked."}
            ] + history
            response = ask_ollama(llm_prompt, os.getenv('OLLAMA_URL', 'http://plexllm-ollama-1:11434'))
            add_message(channel_id, "assistant", bot.user.name, response)
            await message.reply(response)
            return
        channel_id = message.channel.id
        add_message(channel_id, "user", message.author.name, message.content)
        await bot.process_commands(message)
