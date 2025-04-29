import discord
from discord import app_commands

# Add all reaction-based commands to the bot

def add_reaction_commands(bot):
    @bot.tree.command(name="funniest", description="Declare the funniest user based on :joy: reactions in this channel")
    @app_commands.describe(days="Number of days to look back, today, yesterday, or 'all' for all time")
    async def funniest(interaction: discord.Interaction, days: str):
        channel = interaction.channel
        await interaction.response.defer(thinking=True)
        if days.lower() == 'all':
            after = None
            before = None
        elif days.lower() == 'today':
            from datetime import datetime, time, timezone
            try:
                from zoneinfo import ZoneInfo
                eastern = ZoneInfo('America/New_York')
            except ImportError:
                import pytz
                eastern = pytz.timezone('America/New_York')
            now_est = datetime.now(eastern)
            today_start_est = datetime.combine(now_est.date(), time(hour=0, minute=0), tzinfo=eastern)
            after = today_start_est.astimezone(timezone.utc)
            before = None
        elif days.lower() == 'yesterday':
            from datetime import datetime, time, timedelta, timezone
            try:
                from zoneinfo import ZoneInfo
                eastern = ZoneInfo('America/New_York')
            except ImportError:
                import pytz
                eastern = pytz.timezone('America/New_York')
            now_est = datetime.now(eastern)
            yesterday_date = now_est.date() - timedelta(days=1)
            y_start_est = datetime.combine(yesterday_date, time(hour=0, minute=0), tzinfo=eastern)
            y_end_est = datetime.combine(now_est.date(), time(hour=0, minute=0), tzinfo=eastern)
            after = y_start_est.astimezone(timezone.utc)
            before = y_end_est.astimezone(timezone.utc)
        else:
            try:
                days_int = int(days)
                from datetime import datetime, timedelta, timezone
                after = datetime.now(timezone.utc) - timedelta(days=days_int)
                before = None
            except ValueError:
                await interaction.followup.send("Please provide a number of days (e.g. 7), 'today', 'yesterday', or 'all'.")
                return
        user_joy_received = {}
        async for msg in channel.history(limit=None, oldest_first=True, after=after, before=before):
            joy_count = 0
            for reaction in msg.reactions:
                is_joy = False
                if str(reaction.emoji) == '😂':
                    is_joy = True
                elif hasattr(reaction.emoji, 'name') and reaction.emoji.name == 'joy':
                    is_joy = True
                elif str(reaction.emoji) == ':joy:':
                    is_joy = True
                if is_joy:
                    joy_count += reaction.count
            if joy_count > 0:
                user_joy_received[msg.author.name] = user_joy_received.get(msg.author.name, 0) + joy_count
        if not user_joy_received:
            await interaction.followup.send("No :joy: reactions found in this channel for the given period.")
            return
        max_joy = max(user_joy_received.values())
        funniest_users = [user for user, count in user_joy_received.items() if count == max_joy]
        leaderboard = sorted(user_joy_received.items(), key=lambda x: x[1], reverse=True)
        leaderboard_str = '\n'.join([f"{i+1}. {user} - {count} :joy:" for i, (user, count) in enumerate(leaderboard)])
        if len(funniest_users) == 1:
            await interaction.followup.send(f"The funniest user is **{funniest_users[0]}** with {max_joy} :joy: reactions received!\n\nLeaderboard:\n{leaderboard_str}")
        else:
            users_str = ', '.join(f"**{user}**" for user in funniest_users)
            await interaction.followup.send(f"It's a tie! The funniest users are {users_str} with {max_joy} :joy: reactions received each!\n\nLeaderboard:\n{leaderboard_str}")

    @bot.tree.command(name="stingy", description="Declare the stingiest user based on who gives out the least :joy: reactions in this channel")
    @app_commands.describe(days="Number of days to look back, today, yesterday, or 'all' for all time")
    async def stingy(interaction: discord.Interaction, days: str):
        channel = interaction.channel
        await interaction.response.defer(thinking=True)
        if days.lower() == 'all':
            after = None
            before = None
        elif days.lower() == 'today':
            from datetime import datetime, time, timezone
            try:
                from zoneinfo import ZoneInfo
                eastern = ZoneInfo('America/New_York')
            except ImportError:
                import pytz
                eastern = pytz.timezone('America/New_York')
            now_est = datetime.now(eastern)
            today_start_est = datetime.combine(now_est.date(), time(hour=0, minute=0), tzinfo=eastern)
            after = today_start_est.astimezone(timezone.utc)
            before = None
        elif days.lower() == 'yesterday':
            from datetime import datetime, time, timedelta, timezone
            try:
                from zoneinfo import ZoneInfo
                eastern = ZoneInfo('America/New_York')
            except ImportError:
                import pytz
                eastern = pytz.timezone('America/New_York')
            now_est = datetime.now(eastern)
            yesterday_date = now_est.date() - timedelta(days=1)
            y_start_est = datetime.combine(yesterday_date, time(hour=0, minute=0), tzinfo=eastern)
            y_end_est = datetime.combine(now_est.date(), time(hour=0, minute=0), tzinfo=eastern)
            after = y_start_est.astimezone(timezone.utc)
            before = y_end_est.astimezone(timezone.utc)
        else:
            try:
                days_int = int(days)
                from datetime import datetime, timedelta, timezone
                after = datetime.now(timezone.utc) - timedelta(days=days_int)
                before = None
            except ValueError:
                await interaction.followup.send("Please provide a number of days (e.g. 7), 'today', 'yesterday', or 'all'.")
                return
        user_joy_given = {}
        users_with_messages = set()
        async for msg in channel.history(limit=None, oldest_first=True, after=after, before=before):
            if not msg.author.bot:
                users_with_messages.add(msg.author.name)
            for reaction in msg.reactions:
                is_joy = False
                if str(reaction.emoji) == '😂':
                    is_joy = True
                elif hasattr(reaction.emoji, 'name') and reaction.emoji.name == 'joy':
                    is_joy = True
                elif str(reaction.emoji) == ':joy:':
                    is_joy = True
                if is_joy:
                    users = []
                    try:
                        users = [user async for user in reaction.users()]
                    except Exception:
                        continue
                    for user in users:
                        if user.bot:
                            continue
                        user_joy_given[user.name] = user_joy_given.get(user.name, 0) + 1
        # Ensure all users with messages are in the dict, even if they gave 0 :joy:
        for user in users_with_messages:
            if user not in user_joy_given:
                user_joy_given[user] = 0
        if not user_joy_given:
            await interaction.followup.send("Everyone is stingy! No :joy: reactions were given in this channel for the given period.")
            return
        min_joy = min(user_joy_given.values())
        stingiest_users = [user for user, count in user_joy_given.items() if count == min_joy]
        leaderboard = sorted(user_joy_given.items(), key=lambda x: x[1])
        leaderboard_str = '\n'.join([f"{i+1}. {user} - {count} :joy:" for i, (user, count) in enumerate(leaderboard)])
        if len(stingiest_users) == 1:
            await interaction.followup.send(f"The stingiest user is **{stingiest_users[0]}** with only {min_joy} :joy: reactions given!\n\nLeaderboard (least to most):\n{leaderboard_str}")
        else:
            users_str = ', '.join(f"**{user}**" for user in stingiest_users)
            await interaction.followup.send(f"It's a tie! The stingiest users are {users_str} with only {min_joy} :joy: reactions given each!\n\nLeaderboard (least to most):\n{leaderboard_str}")

    @bot.tree.command(name="agreeable", description="Declare the most agreeable user based on :thumbsup: reactions in this channel")
    @app_commands.describe(days="Number of days to look back, today, yesterday, or 'all' for all time")
    async def agreeable(interaction: discord.Interaction, days: str):
        channel = interaction.channel
        await interaction.response.defer(thinking=True)
        # Timeframe logic (same as funniest)
        if days.lower() == 'all':
            after = None
            before = None
        elif days.lower() == 'today':
            from datetime import datetime, time, timezone
            try:
                from zoneinfo import ZoneInfo
                eastern = ZoneInfo('America/New_York')
            except ImportError:
                import pytz
                eastern = pytz.timezone('America/New_York')
            now_est = datetime.now(eastern)
            today_start_est = datetime.combine(now_est.date(), time(hour=0, minute=0), tzinfo=eastern)
            after = today_start_est.astimezone(timezone.utc)
            before = None
        elif days.lower() == 'yesterday':
            from datetime import datetime, time, timedelta, timezone
            try:
                from zoneinfo import ZoneInfo
                eastern = ZoneInfo('America/New_York')
            except ImportError:
                import pytz
                eastern = pytz.timezone('America/New_York')
            now_est = datetime.now(eastern)
            yesterday_date = now_est.date() - timedelta(days=1)
            y_start_est = datetime.combine(yesterday_date, time(hour=0, minute=0), tzinfo=eastern)
            y_end_est = datetime.combine(now_est.date(), time(hour=0, minute=0), tzinfo=eastern)
            after = y_start_est.astimezone(timezone.utc)
            before = y_end_est.astimezone(timezone.utc)
        else:
            try:
                days_int = int(days)
                from datetime import datetime, timedelta, timezone
                after = datetime.now(timezone.utc) - timedelta(days=days_int)
                before = None
            except ValueError:
                await interaction.followup.send("Please provide a number of days (e.g. 7), 'today', 'yesterday', or 'all'.")
                return
        user_thumbsup_received = {}
        async for msg in channel.history(limit=None, oldest_first=True, after=after, before=before):
            thumbs_count = 0
            for reaction in msg.reactions:
                is_thumbsup = False
                if str(reaction.emoji) == '👍':
                    is_thumbsup = True
                elif hasattr(reaction.emoji, 'name') and reaction.emoji.name == 'thumbsup':
                    is_thumbsup = True
                elif str(reaction.emoji) == ':thumbsup:':
                    is_thumbsup = True
                if is_thumbsup:
                    thumbs_count += reaction.count
            if thumbs_count > 0:
                user_thumbsup_received[msg.author.name] = user_thumbsup_received.get(msg.author.name, 0) + thumbs_count
        if not user_thumbsup_received:
            await interaction.followup.send("No :thumbsup: reactions found in this channel for the given period.")
            return
        max_thumbs = max(user_thumbsup_received.values())
        agreeable_users = [user for user, count in user_thumbsup_received.items() if count == max_thumbs]
        leaderboard = sorted(user_thumbsup_received.items(), key=lambda x: x[1], reverse=True)
        leaderboard_str = '\n'.join([f"{i+1}. {user} - {count} :thumbsup:" for i, (user, count) in enumerate(leaderboard)])
        if len(agreeable_users) == 1:
            await interaction.followup.send(f"The most agreeable user is **{agreeable_users[0]}** with {max_thumbs} :thumbsup: reactions received!\n\nLeaderboard:\n{leaderboard_str}")
        else:
            users_str = ', '.join(f"**{user}**" for user in agreeable_users)
            await interaction.followup.send(f"It's a tie! The most agreeable users are {users_str} with {max_thumbs} :thumbsup: reactions received each!\n\nLeaderboard:\n{leaderboard_str}")

    @bot.tree.command(name="disagreeable", description="Declare the most disagreeable user based on :thumbsdown: reactions in this channel")
    @app_commands.describe(days="Number of days to look back, today, yesterday, or 'all' for all time")
    async def disagreeable(interaction: discord.Interaction, days: str):
        channel = interaction.channel
        await interaction.response.defer(thinking=True)
        # Timeframe logic (same as funniest)
        if days.lower() == 'all':
            after = None
            before = None
        elif days.lower() == 'today':
            from datetime import datetime, time, timezone
            try:
                from zoneinfo import ZoneInfo
                eastern = ZoneInfo('America/New_York')
            except ImportError:
                import pytz
                eastern = pytz.timezone('America/New_York')
            now_est = datetime.now(eastern)
            today_start_est = datetime.combine(now_est.date(), time(hour=0, minute=0), tzinfo=eastern)
            after = today_start_est.astimezone(timezone.utc)
            before = None
        elif days.lower() == 'yesterday':
            from datetime import datetime, time, timedelta, timezone
            try:
                from zoneinfo import ZoneInfo
                eastern = ZoneInfo('America/New_York')
            except ImportError:
                import pytz
                eastern = pytz.timezone('America/New_York')
            now_est = datetime.now(eastern)
            yesterday_date = now_est.date() - timedelta(days=1)
            y_start_est = datetime.combine(yesterday_date, time(hour=0, minute=0), tzinfo=eastern)
            y_end_est = datetime.combine(now_est.date(), time(hour=0, minute=0), tzinfo=eastern)
            after = y_start_est.astimezone(timezone.utc)
            before = y_end_est.astimezone(timezone.utc)
        else:
            try:
                days_int = int(days)
                from datetime import datetime, timedelta, timezone
                after = datetime.now(timezone.utc) - timedelta(days=days_int)
                before = None
            except ValueError:
                await interaction.followup.send("Please provide a number of days (e.g. 7), 'today', 'yesterday', or 'all'.")
                return
        user_thumbsdown_received = {}
        async for msg in channel.history(limit=None, oldest_first=True, after=after, before=before):
            thumbsdown_count = 0
            for reaction in msg.reactions:
                is_thumbsdown = False
                if str(reaction.emoji) == '👎':
                    is_thumbsdown = True
                elif hasattr(reaction.emoji, 'name') and reaction.emoji.name == 'thumbsdown':
                    is_thumbsdown = True
                elif str(reaction.emoji) == ':thumbsdown:':
                    is_thumbsdown = True
                if is_thumbsdown:
                    thumbsdown_count += reaction.count
            if thumbsdown_count > 0:
                user_thumbsdown_received[msg.author.name] = user_thumbsdown_received.get(msg.author.name, 0) + thumbsdown_count
        if not user_thumbsdown_received:
            await interaction.followup.send("No :thumbsdown: reactions found in this channel for the given period.")
            return
        max_thumbsdown = max(user_thumbsdown_received.values())
        disagreeable_users = [user for user, count in user_thumbsdown_received.items() if count == max_thumbsdown]
        leaderboard = sorted(user_thumbsdown_received.items(), key=lambda x: x[1], reverse=True)
        leaderboard_str = '\n'.join([f"{i+1}. {user} - {count} :thumbsdown:" for i, (user, count) in enumerate(leaderboard)])
        if len(disagreeable_users) == 1:
            await interaction.followup.send(f"The most disagreeable user is **{disagreeable_users[0]}** with {max_thumbsdown} :thumbsdown: reactions received!\n\nLeaderboard:\n{leaderboard_str}")
        else:
            users_str = ', '.join(f"**{user}**" for user in disagreeable_users)
            await interaction.followup.send(f"It's a tie! The most disagreeable users are {users_str} with {max_thumbsdown} :thumbsdown: reactions received each!\n\nLeaderboard:\n{leaderboard_str}")
