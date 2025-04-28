import discord
from discord import app_commands
import asyncio
from ollama_client import ask_ollama
from db import add_message, get_history, get_messages_after_user_last, get_messages_for_timeframe
from sports.mlb import get_live_mlb_games
from sports.nba import get_live_nba_games
from sports.nfl import get_live_nfl_games
import re

# These will be injected from the main bot file
OLLAMA_URL = None
HISTORY_LIMIT = None

def add_llm_commands(bot, ollama_url, history_limit):
    global OLLAMA_URL, HISTORY_LIMIT
    OLLAMA_URL = ollama_url
    HISTORY_LIMIT = history_limit

    @bot.tree.command(name="chat", description="Chat with the llama")
    @app_commands.describe(message="Your message to the llama")
    async def chat(interaction: discord.Interaction, message: str):
        await interaction.response.defer()
        channel_id = interaction.channel_id
        add_message(channel_id, "user", interaction.user.name, message)
        SHORT_HISTORY_LIMIT = 8
        history = get_history(channel_id, SHORT_HISTORY_LIMIT)
        # Prefix username to content for each message
        formatted_history = []
        for msg in history:
            role = msg.get("role", "user")
            username = msg.get("username", "user")
            content = msg.get("content", "")
            formatted_history.append({"role": role, "content": f"{username}: {content}"})
        llm_prompt = [
            {"role": "system", "content": "You are a helpful assistant. Answer the user's request directly and concisely. Do not summarize previous conversation unless asked."}
        ] + formatted_history
        try:
            response = await asyncio.to_thread(ask_ollama, llm_prompt, OLLAMA_URL)
        except Exception as e:
            response = f"Error: {e}"
        add_message(channel_id, "assistant", bot.user.name, response)
        await interaction.followup.send(response)

    @bot.tree.command(name="tldr", description="Summarize everything since you last sent a message in this channel")
    async def tldr(interaction: discord.Interaction):
        channel_id = interaction.channel_id
        username = interaction.user.name
        messages = get_messages_after_user_last(channel_id, username)
        if not messages:
            await interaction.response.send_message("No new messages since your last message.")
            return
        summary_prompt = [{
            "role": "system",
            "content": "Summarize the following conversation for me. Be concise and to the point. 50 words or less please."
        }] + messages
        await interaction.response.defer()
        summary = ask_ollama(summary_prompt, OLLAMA_URL)
        import re
        summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL)
        summary = re.sub(r'<think>|</think>', '', summary)
        summary = summary.strip()
        if len(summary) > 1900:
            summary = summary[:1900] + "..."
        await interaction.followup.send(f"**TL;DR:**\n{summary}")

    @bot.tree.command(name="summarize", description="Summarize all messages in this channel for a given timeframe (today, yesterday, this_month, all)")
    @app_commands.describe(timeframe="Timeframe to summarize: today, yesterday, this_month, or all")
    async def summarize(interaction: discord.Interaction, timeframe: str):
        channel_id = interaction.channel_id
        valid_timeframes = {"today", "yesterday", "this_month", "all"}
        if timeframe not in valid_timeframes:
            await interaction.response.send_message("Please provide a valid timeframe: today, yesterday, this_month, or all.")
            return
        messages = get_messages_for_timeframe(channel_id, timeframe)
        if not messages:
            await interaction.response.send_message(f"No messages found for timeframe '{timeframe}'.")
            return
        summary_prompt = [{
            "role": "system",
            "content": f"Summarize the following conversation for the timeframe '{timeframe}'. Be concise and to the point. 500 words or less."
        }] + messages
        await interaction.response.defer()
        summary = ask_ollama(summary_prompt, OLLAMA_URL)
        import re
        summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL)
        summary = re.sub(r'<think>|</think>', '', summary)
        summary = summary.strip()
        if len(summary) > 1900:
            summary = summary[:1900] + "..."
        await interaction.followup.send(f"**Summary for {timeframe}:**\n{summary}")

    @bot.tree.context_menu(name="ELI5 (Explain Like I'm 5)")
    async def eli5(interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer()
        prompt = [
            {"role": "system", "content": "Explain the following message as if you are talking to a 5-year-old. Use simple words and keep it short."},
            {"role": "user", "content": message.content}
        ]
        explanation = ask_ollama(prompt, OLLAMA_URL)
        import re
        explanation = re.sub(r'<think>.*?</think>', '', explanation, flags=re.DOTALL)
        explanation = re.sub(r'<think>|</think>', '', explanation)
        explanation = explanation.strip()
        if len(explanation) > 1900:
            explanation = explanation[:1900] + "..."
        await interaction.followup.send(f"**Original message:**\n> {message.content}\n\n**ELI5:**\n{explanation}", ephemeral=True)
