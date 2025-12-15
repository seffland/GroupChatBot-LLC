import discord
from discord import app_commands
import asyncio
from ollama_client import ask_ollama
from db import add_message, get_history, get_messages_after_user_last, get_messages_for_timeframe, get_channel_personality, set_channel_personality
from sports.mlb import get_live_mlb_games
from sports.nba import get_live_nba_games
from sports.nfl import get_live_nfl_games
import re
from util import fix_mojibake  # Import the mojibake fixer
import os

# These will be injected from the main bot file
OLLAMA_URL = None
HISTORY_LIMIT = None

def add_llm_commands(bot, ollama_url, history_limit):
    global OLLAMA_URL, HISTORY_LIMIT
    OLLAMA_URL = ollama_url
    HISTORY_LIMIT = history_limit

    # Helper to trim history by total characters (proxy for tokens)
    def trim_history_by_chars(history, max_chars=9000):
        result = []
        total = 0
        for msg in reversed(history):
            msg_str = f"{msg.get('username', 'user')}: {msg.get('content', '')}"
            if total + len(msg_str) > max_chars:
                break
            result.insert(0, msg)
            total += len(msg_str)
        return result

    @bot.tree.command(name="chat", description="Chat with the llama")
    @app_commands.describe(message="Your message to the llama")
    async def chat(interaction: discord.Interaction, message: str):
        await interaction.response.defer()
        channel_id = interaction.channel_id if interaction.channel_id is not None else 0
        add_message(channel_id, "user", interaction.user.name, message)
        # Use channel personality if set, else default
        system_prompt = get_channel_personality(channel_id) or "You are a helpful assistant. Answer the user's request directly and concisely."
<<<<<<< HEAD
        # Fetch recent message history for context (reduced to 5 messages to avoid confusion)
        history = get_history(channel_id, limit=5)
        # Strong instruction so model answers only the latest user message
        guard = (
            "Important: Use the conversation history only for context. "
            "Answer ONLY the user's most recent message below. Do NOT repeat, summarize, or respond to earlier messages unless explicitly asked."
        )
        # Build a compact history block (context only)
        history_items = history[:-1]  # skip the last entry which is the current message we just stored
        history_text = ""
        for msg in history_items:
            if msg['role'] == 'user':
                history_text += f"USER ({msg.get('username','user')}): {msg.get('content','')}\n"
            else:
                history_text += f"ASSISTANT: {msg.get('content','')}\n"
        # System prompt with guard followed by a single system message containing the context
        llm_prompt = [{"role": "system", "content": system_prompt + "\n\n" + guard}]
        if history_text:
            llm_prompt.append({"role": "system", "content": "Conversation history (context only):\n" + history_text})
        # Add current message as the single user turn the LLM should answer
=======
        # Fetch recent message history for context
        history = get_history(channel_id, limit=20)
        llm_prompt = [{"role": "system", "content": system_prompt}]
        # Add conversation history (excluding the message we just added)
        for msg in history[:-1]:  # Skip the last message since that's the one we just added
            if msg['role'] == 'user':
                llm_prompt.append({"role": "user", "content": f"{msg['username']}: {msg['content']}"})
            else:
                llm_prompt.append({"role": "assistant", "content": msg['content']})
        # Trim history by character count to stay within limits
        llm_prompt = trim_history_by_chars(llm_prompt, max_chars=9000)
        # Add current message
>>>>>>> 83041854d4debc7a33a75d225530313f7bde20b9
        llm_prompt.append({"role": "user", "content": f"{interaction.user.name}: {message}"})
        try:
            response = await asyncio.to_thread(ask_ollama, llm_prompt, OLLAMA_URL)
        except Exception as e:
            response = f"Error: {e}"
        response = fix_mojibake(response)
        add_message(channel_id, "assistant", bot.user.name, response)
        await interaction.followup.send(response)

    @bot.tree.command(name="tldr", description="Summarize everything since you last sent a message in this channel")
    async def tldr(interaction: discord.Interaction):
        channel_id = interaction.channel_id if interaction.channel_id is not None else 0
        username = interaction.user.name
        messages = get_messages_after_user_last(channel_id, username)
        if not messages:
            await interaction.response.send_message("No new messages since your last message.")
            return
        # Use channel personality if set, else default
        system_prompt = get_channel_personality(channel_id) or "Summarize the following conversation for me. Be concise and to the point. 50 words or less please."
        summary_prompt = [{
            "role": "system",
            "content": system_prompt
        }] + messages
        await interaction.response.defer()
        summary = ask_ollama(summary_prompt, OLLAMA_URL)
        summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL)
        summary = re.sub(r'<think>|</think>', '', summary)
        summary = summary.strip()
        summary = fix_mojibake(summary)
        if len(summary) > 1900:
            summary = summary[:1900] + "..."
        await interaction.followup.send(f"**TL;DR:**\n{summary}")

    @bot.tree.command(name="summarize", description="Summarize all messages in this channel for a given timeframe (today, yesterday, this_month, all)")
    @app_commands.describe(timeframe="Timeframe to summarize: today, yesterday, this_month, or all")
    async def summarize(interaction: discord.Interaction, timeframe: str):
        channel_id = interaction.channel_id if interaction.channel_id is not None else 0
        valid_timeframes = {"today", "yesterday", "this_month", "all"}
        if timeframe not in valid_timeframes:
            await interaction.response.send_message("Please provide a valid timeframe: today, yesterday, this_month, or all.")
            return
        messages = get_messages_for_timeframe(channel_id, timeframe)
        if not messages:
            await interaction.response.send_message(f"No messages found for timeframe '{timeframe}'.")
            return
        # Use channel personality if set, else default
        system_prompt = get_channel_personality(channel_id) or f"Summarize the following conversation for the timeframe '{timeframe}'. Be concise and to the point. 500 words or less."
        summary_prompt = [{
            "role": "system",
            "content": system_prompt
        }] + messages
        await interaction.response.defer()
        summary = await asyncio.to_thread(ask_ollama, summary_prompt, OLLAMA_URL)
        summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL)
        summary = re.sub(r'<think>|</think>', '', summary)
        summary = summary.strip()
        summary = fix_mojibake(summary)
        if len(summary) > 1900:
            summary = summary[:1900] + "..."
        await interaction.followup.send(f"**Summary for {timeframe}:**\n{summary}")

    @bot.tree.command(name="setpersonality", description="Set the chatbot personality for this channel (admin only)")
    @app_commands.describe(personality="The new personality prompt for the chatbot in this channel.")
    async def setpersonality(interaction: discord.Interaction, personality: str):
        OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "0"))
        additional_admins_env = os.getenv("ADDITIONAL_ADMIN_IDS", "")
        ADDITIONAL_ADMINS = set()
        if additional_admins_env:
            ADDITIONAL_ADMINS = {int(uid) for uid in additional_admins_env.split(",") if uid.strip().isdigit()}
        if interaction.user.id != OWNER_USER_ID and interaction.user.id not in ADDITIONAL_ADMINS:
            await interaction.response.send_message("You are not authorized to set the personality.")
            return
        channel_id = interaction.channel_id if interaction.channel_id is not None else 0
        set_channel_personality(channel_id, personality)
        await interaction.response.send_message(f"Personality for this channel set to: '{personality}'")

    @bot.tree.context_menu(name="ELI5 (Explain Like I'm 5)")
    async def eli5(interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer()
        channel_id = interaction.channel_id if interaction.channel_id is not None else 0
        # Use channel personality if set, else default
        system_prompt = get_channel_personality(channel_id) or "Explain the following message as if you are talking to a 5-year-old. Use simple words and keep it short."
        prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message.content}
        ]
        explanation = ask_ollama(prompt, OLLAMA_URL)
        explanation = re.sub(r'<think>.*?</think>', '', explanation, flags=re.DOTALL)
        explanation = re.sub(r'<think>|</think>', '', explanation)
        explanation = explanation.strip()
        explanation = fix_mojibake(explanation)
        if len(explanation) > 1900:
            explanation = explanation[:1900] + "..."
        await interaction.followup.send(f"**Original message:**\n> {message.content}\n\n**ELI5:**\n{explanation}", ephemeral=True)
