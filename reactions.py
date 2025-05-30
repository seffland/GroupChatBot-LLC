import discord
from discord import app_commands
import asyncio

# Add all reaction-based commands to the bot

def add_reaction_commands(bot):
    @bot.tree.command(name="funniest", description="Declare the funniest user based on :joy: reactions in this channel")
    @app_commands.describe(days="Number of days to look back, today, yesterday, or 'all' for all time")
    async def funniest(interaction: discord.Interaction, days: str):
        channel = interaction.channel
        await interaction.response.defer(thinking=True)
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send("This command can only be used in text channels.")
            return
        
        # Parse time frame
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
          # For 'all' time queries, add progress updates (no message limit)
        if days.lower() == 'all':
            # No limit - analyze all messages in channel history
            limit = None
            await interaction.edit_original_response(content="⏳ Analyzing ALL channel history for :joy: reactions... This may take several minutes for large channels.")
        else:
            limit = None

        message_count = 0
        last_update = 0
        
        async for msg in channel.history(limit=limit, oldest_first=True, after=after, before=before):
            message_count += 1
            
            # Send progress update every 1500 messages for 'all' queries
            if days.lower() == 'all' and message_count - last_update >= 1500:
                await interaction.edit_original_response(content=f"⏳ Processed {message_count:,} messages so far...")
                last_update = message_count
                # Add a small delay to prevent rate limiting
                await asyncio.sleep(0.1)
            
            joy_count = 0
            for reaction in msg.reactions:
                is_joy = False
                if str(reaction.emoji) == '😂':
                    is_joy = True
                elif not isinstance(reaction.emoji, str) and getattr(reaction.emoji, 'name', None) == 'joy':
                    is_joy = True
                elif isinstance(reaction.emoji, str) and reaction.emoji == ':joy:':
                    is_joy = True
                if is_joy:
                    joy_count += reaction.count
            if joy_count > 0:
                user_joy_received[msg.author.name] = user_joy_received.get(msg.author.name, 0) + joy_count
        
        if not user_joy_received:
            await interaction.edit_original_response(content="No :joy: reactions found in this channel for the given period.")
            return
        
        max_joy = max(user_joy_received.values())
        funniest_users = [user for user, count in user_joy_received.items() if count == max_joy]
        leaderboard = sorted(user_joy_received.items(), key=lambda x: x[1], reverse=True)
        leaderboard_str = '\n'.join([f"{i+1}. {user} - {count} :joy:" for i, (user, count) in enumerate(leaderboard)])
        
        # Add footer with performance info
        footer = f"\n\n📊 Analyzed {message_count:,} messages"
        if days.lower() == 'all':
            footer += " (complete channel history)"
        
        if len(funniest_users) == 1:
            await interaction.edit_original_response(content=f"The funniest user is **{funniest_users[0]}** with {max_joy} :joy: reactions received!\n\nLeaderboard:\n{leaderboard_str}{footer}")
        else:
            users_str = ', '.join(f"**{user}**" for user in funniest_users)
            await interaction.edit_original_response(content=f"It's a tie! The funniest users are {users_str} with {max_joy} :joy: reactions received each!\n\nLeaderboard:\n{leaderboard_str}{footer}")

    @bot.tree.command(name="stingy", description="Declare the stingiest user based on who gives out the least reactions in this channel")
    @app_commands.describe(days="Number of days to look back, today, yesterday, or 'all' for all time")
    async def stingy(interaction: discord.Interaction, days: str):
        channel = interaction.channel
        await interaction.response.defer(thinking=True)
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send("This command can only be used in text channels.")
            return
        
        # Parse time frame (same logic as funniest)
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
        
        user_reactions_given = {}
        users_with_messages = set()
        users_who_reacted = set()
          # For 'all' time queries, add progress updates (no message limit)
        if days.lower() == 'all':
            # No limit - analyze all messages in channel history
            limit = None
            await interaction.edit_original_response(content="⏳ Analyzing ALL channel history for reaction patterns... This may take several minutes for large channels.")
        else:
            limit = None

        message_count = 0
        last_update = 0
        
        async for msg in channel.history(limit=limit, oldest_first=True, after=after, before=before):
            message_count += 1
            
            # Send progress update every 1500 messages for 'all' queries
            if days.lower() == 'all' and message_count - last_update >= 1500:
                await interaction.edit_original_response(content=f"⏳ Processed {message_count:,} messages so far...")
                last_update = message_count
                # Add a small delay to prevent rate limiting
                await asyncio.sleep(0.1)
            
            # Track users who sent messages
            if not msg.author.bot:
                users_with_messages.add(msg.author.name)
            
            # Track users who gave reactions
            for reaction in msg.reactions:
                users = []
                try:
                    users = [user async for user in reaction.users()]
                except Exception:
                    continue
                for user in users:
                    if user.bot:
                        continue
                    users_who_reacted.add(user.name)
                    user_reactions_given[user.name] = user_reactions_given.get(user.name, 0) + 1
        
        # Ensure all users who sent messages OR reacted are in the dict, even if they gave 0 reactions
        all_active_users = users_with_messages.union(users_who_reacted)
        for user in all_active_users:
            if user not in user_reactions_given:
                user_reactions_given[user] = 0
        
        if not user_reactions_given:
            await interaction.edit_original_response(content="Everyone is stingy! No reactions were given in this channel for the given period.")
            return
        
        min_reactions = min(user_reactions_given.values())
        stingiest_users = [user for user, count in user_reactions_given.items() if count == min_reactions]
        leaderboard = sorted(user_reactions_given.items(), key=lambda x: x[1])
        leaderboard_str = '\n'.join([f"{i+1}. {user} - {count} reactions" for i, (user, count) in enumerate(leaderboard)])
          # Add footer with performance info
        footer = f"\n\n📊 Analyzed {message_count:,} messages"
        if days.lower() == 'all':
            footer += " (complete channel history)"
        
        if len(stingiest_users) == 1:
            await interaction.edit_original_response(content=f"The stingiest user is **{stingiest_users[0]}** with only {min_reactions} reactions given!\n\nLeaderboard (least to most):\n{leaderboard_str}{footer}")
        else:
            users_str = ', '.join(f"**{user}**" for user in stingiest_users)
            await interaction.edit_original_response(content=f"It's a tie! The stingiest users are {users_str} with only {min_reactions} reactions given each!\n\nLeaderboard (least to most):\n{leaderboard_str}{footer}")

    @bot.tree.command(name="disagreeable", description="Declare the most disagreeable user based on :thumbsdown: reactions in this channel")
    @app_commands.describe(days="Number of days to look back, today, yesterday, or 'all' for all time")
    async def disagreeable(interaction: discord.Interaction, days: str):
        channel = interaction.channel
        await interaction.response.defer(thinking=True)
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send("This command can only be used in text channels.")
            return
        
        # Parse time frame (same logic as funniest)
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
          # For 'all' time queries, add progress updates (no message limit)
        if days.lower() == 'all':
            # No limit - analyze all messages in channel history
            limit = None
            await interaction.edit_original_response(content="⏳ Analyzing ALL channel history for :thumbsdown: reactions... This may take several minutes for large channels.")
        else:
            limit = None

        message_count = 0
        last_update = 0
        
        async for msg in channel.history(limit=limit, oldest_first=True, after=after, before=before):
            message_count += 1
            
            # Send progress update every 1500 messages for 'all' queries
            if days.lower() == 'all' and message_count - last_update >= 1500:
                await interaction.edit_original_response(content=f"⏳ Processed {message_count:,} messages so far...")
                last_update = message_count
                # Add a small delay to prevent rate limiting
                await asyncio.sleep(0.1)
            
            thumbsdown_count = 0
            for reaction in msg.reactions:
                is_thumbsdown = False
                if str(reaction.emoji) == '👎':
                    is_thumbsdown = True
                elif not isinstance(reaction.emoji, str) and getattr(reaction.emoji, 'name', None) == 'thumbsdown':
                    is_thumbsdown = True
                elif str(reaction.emoji) == ':thumbsdown:':
                    is_thumbsdown = True
                if is_thumbsdown:
                    thumbsdown_count += reaction.count
            if thumbsdown_count > 0:
                user_thumbsdown_received[msg.author.name] = user_thumbsdown_received.get(msg.author.name, 0) + thumbsdown_count
        
        if not user_thumbsdown_received:
            await interaction.edit_original_response(content="No :thumbsdown: reactions found in this channel for the given period.")
            return
        
        max_thumbsdown = max(user_thumbsdown_received.values())
        disagreeable_users = [user for user, count in user_thumbsdown_received.items() if count == max_thumbsdown]
        leaderboard = sorted(user_thumbsdown_received.items(), key=lambda x: x[1], reverse=True)
        leaderboard_str = '\n'.join([f"{i+1}. {user} - {count} :thumbsdown:" for i, (user, count) in enumerate(leaderboard)])
        
        # Add footer with performance info
        footer = f"\n\n📊 Analyzed {message_count:,} messages"
        if days.lower() == 'all':
            footer += " (complete channel history)"
        
        if len(disagreeable_users) == 1:
            await interaction.edit_original_response(content=f"The most disagreeable user is **{disagreeable_users[0]}** with {max_thumbsdown} :thumbsdown: reactions received!\n\nLeaderboard:\n{leaderboard_str}{footer}")
        else:
            users_str = ', '.join(f"**{user}**" for user in disagreeable_users)
            await interaction.edit_original_response(content=f"It's a tie! The most disagreeable users are {users_str} with {max_thumbsdown} :thumbsdown: reactions received each!\n\nLeaderboard:\n{leaderboard_str}{footer}")

    @bot.tree.command(name="loved", description="Declare the most loved user based on :heart: reactions in this channel")
    @app_commands.describe(days="Number of days to look back, today, yesterday, or 'all' for all time")
    async def loved(interaction: discord.Interaction, days: str):
        channel = interaction.channel
        await interaction.response.defer(thinking=True)
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send("This command can only be used in text channels.")
            return
        
        # Parse time frame (same logic as funniest)
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
        
        user_heart_received = {}
          # For 'all' time queries, add progress updates (no message limit)
        if days.lower() == 'all':
            # No limit - analyze all messages in channel history
            limit = None
            await interaction.edit_original_response(content="⏳ Analyzing ALL channel history for :heart: reactions... This may take several minutes for large channels.")
        else:
            limit = None

        message_count = 0
        last_update = 0
        
        async for msg in channel.history(limit=limit, oldest_first=True, after=after, before=before):
            message_count += 1
            
            # Send progress update every 1500 messages for 'all' queries
            if days.lower() == 'all' and message_count - last_update >= 1500:
                await interaction.edit_original_response(content=f"⏳ Processed {message_count:,} messages so far...")
                last_update = message_count
                # Add a small delay to prevent rate limiting
                await asyncio.sleep(0.1)
            
            heart_count = 0
            for reaction in msg.reactions:
                is_heart = False
                if str(reaction.emoji) == '❤️':
                    is_heart = True
                elif not isinstance(reaction.emoji, str) and getattr(reaction.emoji, 'name', None) == 'heart':
                    is_heart = True
                elif isinstance(reaction.emoji, str) and reaction.emoji == ':heart:':
                    is_heart = True
                if is_heart:
                    heart_count += reaction.count
            if heart_count > 0:
                user_heart_received[msg.author.name] = user_heart_received.get(msg.author.name, 0) + heart_count
        
        if not user_heart_received:
            await interaction.edit_original_response(content="No :heart: reactions found in this channel for the given period.")
            return
        
        max_hearts = max(user_heart_received.values())
        loved_users = [user for user, count in user_heart_received.items() if count == max_hearts]
        leaderboard = sorted(user_heart_received.items(), key=lambda x: x[1], reverse=True)
        leaderboard_str = '\n'.join([f"{i+1}. {user} - {count} :heart:" for i, (user, count) in enumerate(leaderboard)])
        
        # Add footer with performance info
        footer = f"\n\n📊 Analyzed {message_count:,} messages"
        if days.lower() == 'all':
            footer += " (complete channel history)"
        
        if len(loved_users) == 1:
            await interaction.edit_original_response(content=f"The most loved user is **{loved_users[0]}** with {max_hearts} :heart: reactions received!\n\nLeaderboard:\n{leaderboard_str}{footer}")
        else:
            users_str = ', '.join(f"**{user}**" for user in loved_users)
            await interaction.edit_original_response(content=f"It's a tie! The most loved users are {users_str} with {max_hearts} :heart: reactions received each!\n\nLeaderboard:\n{leaderboard_str}{footer}")

    @bot.tree.command(name="agreeable", description="Declare the most agreeable user based on :thumbsup: reactions in this channel")
    @app_commands.describe(days="Number of days to look back, today, yesterday, or 'all' for all time")
    async def agreeable(interaction: discord.Interaction, days: str):
        channel = interaction.channel
        await interaction.response.defer(thinking=True)
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send("This command can only be used in text channels.")
            return
        
        # Parse time frame (same logic as funniest)
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
          # For 'all' time queries, add progress updates (no message limit)
        if days.lower() == 'all':
            # No limit - analyze all messages in channel history
            limit = None
            await interaction.edit_original_response(content="⏳ Analyzing ALL channel history for :thumbsup: reactions... This may take several minutes for large channels.")
        else:
            limit = None

        message_count = 0
        last_update = 0
        
        async for msg in channel.history(limit=limit, oldest_first=True, after=after, before=before):
            message_count += 1
            
            # Send progress update every 1500 messages for 'all' queries
            if days.lower() == 'all' and message_count - last_update >= 1500:
                await interaction.edit_original_response(content=f"⏳ Processed {message_count:,} messages so far...")
                last_update = message_count
                # Add a small delay to prevent rate limiting
                await asyncio.sleep(0.1)
            
            thumbsup_count = 0
            for reaction in msg.reactions:
                is_thumbsup = False
                if str(reaction.emoji) == '👍':
                    is_thumbsup = True
                elif not isinstance(reaction.emoji, str) and getattr(reaction.emoji, 'name', None) == 'thumbsup':
                    is_thumbsup = True
                elif str(reaction.emoji) == ':thumbsup:':
                    is_thumbsup = True
                if is_thumbsup:
                    thumbsup_count += reaction.count
            if thumbsup_count > 0:
                user_thumbsup_received[msg.author.name] = user_thumbsup_received.get(msg.author.name, 0) + thumbsup_count
        
        if not user_thumbsup_received:
            await interaction.edit_original_response(content="No :thumbsup: reactions found in this channel for the given period.")
            return
        
        max_thumbsup = max(user_thumbsup_received.values())
        agreeable_users = [user for user, count in user_thumbsup_received.items() if count == max_thumbsup]
        leaderboard = sorted(user_thumbsup_received.items(), key=lambda x: x[1], reverse=True)
        leaderboard_str = '\n'.join([f"{i+1}. {user} - {count} :thumbsup:" for i, (user, count) in enumerate(leaderboard)])
        
        # Add footer with performance info
        footer = f"\n\n📊 Analyzed {message_count:,} messages"
        if days.lower() == 'all':
            footer += " (complete channel history)"
        
        if len(agreeable_users) == 1:
            await interaction.edit_original_response(content=f"The most agreeable user is **{agreeable_users[0]}** with {max_thumbsup} :thumbsup: reactions received!\n\nLeaderboard:\n{leaderboard_str}{footer}")
        else:
            users_str = ', '.join(f"**{user}**" for user in agreeable_users)
            await interaction.edit_original_response(content=f"It's a tie! The most agreeable users are {users_str} with {max_thumbsup} :thumbsup: reactions received each!\n\nLeaderboard:\n{leaderboard_str}{footer}")
