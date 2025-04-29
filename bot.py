import discord
from discord.ext import commands
import os
from dev import add_dev_commands
from sports.f1 import add_f1_command
from finance import add_finance_commands
from sports.nascar import add_nascar_commands
from sports.nba import add_nba_commands
from sports.mlb import add_mlb_commands
from sports.nfl import add_nfl_commands
from sports.pga import add_pga_commands
from on_message import setup_on_message
from reactions import add_reaction_commands
from historian import add_historian_commands
from llm import add_llm_commands
from reccomendations import add_recommendations_command

TOKEN = os.getenv('DISCORD_TOKEN')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://plexllm-ollama-1:11434')
HISTORY_LIMIT = 1000  # Number of messages to keep per channel
DEVELOPMENT_SERVER_ID = os.getenv('DEVELOPMENT_SERVER_ID')
PRODUCTION_SERVER_ID = os.getenv('PRODUCTION_SERVER_ID')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

add_f1_command(bot)
add_dev_commands(bot)
add_finance_commands(bot)
add_nascar_commands(bot)
add_nba_commands(bot)
add_mlb_commands(bot)
add_nfl_commands(bot)
add_pga_commands(bot)
add_reaction_commands(bot)
add_historian_commands(bot)
setup_on_message(bot, HISTORY_LIMIT)
add_llm_commands(bot, OLLAMA_URL, HISTORY_LIMIT)
add_recommendations_command(bot)

@bot.event
async def on_ready():
    #print(f'Logged in as {bot.user}')
    try:
        # Always sync to the development server for fast iteration,
        # but also sync globally if PRODUCTION_SERVER_ID is set.
        if DEVELOPMENT_SERVER_ID:
            guild_obj = discord.Object(id=int(DEVELOPMENT_SERVER_ID))
            synced = await bot.tree.sync(guild=guild_obj)
            #print(f'Synced {len(synced)} command(s) to development server {DEVELOPMENT_SERVER_ID}')
        if PRODUCTION_SERVER_ID:
            # Optionally sync to a production server for testing before global
            prod_guild_obj = discord.Object(id=int(PRODUCTION_SERVER_ID))
            synced_prod = await bot.tree.sync(guild=prod_guild_obj)
            #print(f'Synced {len(synced_prod)} command(s) to production server {PRODUCTION_SERVER_ID}')
        # Always sync globally as well
        synced_global = await bot.tree.sync()
        #print(f'Synced {len(synced_global)} command(s) globally')
    except Exception as e:
        print("Error during command sync:", e)

if __name__ == "__main__":
    bot.run(TOKEN)
