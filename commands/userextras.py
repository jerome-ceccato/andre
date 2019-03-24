#!/usr/bin/env python3

import asyncio
import pytz
import datetime
import pycountry
import discord
import re
from discord.ext import commands
from discord.ext.commands import errors

from utils import database, utils, shared, checks

class UserdbExtras:
    def __init__(self, bot):
        self.bot = bot
        self.timeout = 300.0

    @commands.command(pass_context=True, aliases=['Extras', 'extra', 'Extra'])
    @checks.is_banned(permission=checks.PermissionLevel.UserData)
    async def extras(self, ctx, subcommand: str = ''):
        if subcommand.lower() == 'setup':
            await self.db_setup(ctx)
        elif subcommand.lower() == 'update':
            await self.db_update(ctx)
        else:
            await self.help(ctx)

    async def help(self, ctx):
        await ctx.bot.say("""Usage:

`!user extras setup` starts the q/a to fill your extras profile
`!user extras update` lets you update part of your extras profile""")

    ###############################
    ### UPDATE
    ###############################

    @commands.command(name='_internal_extras_update', pass_context=True, hidden=True)
    @checks.is_banned(permission=checks.PermissionLevel.UserData)
    async def db_update(self, ctx):
        await shared.state.lock_user(ctx, '!user extras update')

        try:
            session = database.new_session()
            user = await self.get_user(ctx, session, ctx.message.author.id)

            extras = session.query(database.Extras).all()
            user_extras = session.query(database.UserExtras).filter(database.UserExtras.user_id == user.id).all()

            if len(extras) == 0:
                await ctx.bot.whisper('No extras available')
                return

            done_extras, new_extras = self.sort_extras(extras, user_extras)

            done_extras_display = '\n'.join(map(lambda x: f'**{x["extra"].id}** - {x["extra"].question}', done_extras))
            new_extras_display = '\n'.join(map(lambda x: f'**{x.id}** - {x.question}', new_extras))

            if not done_extras_display:
                done_extras_display = 'None'
            if not new_extras_display:
                new_extras_display = 'None'

            message = f"""To answer a question, simply type its identifier.
If you do not want to answer a question, simply type `-` and I will skip it (and remove your previous answer if any).
If at any point you want to stop editing questions, type `!quit` (or `done` when selecting questions).
Questions you've already answered:
{done_extras_display}

New questions:
{new_extras_display}"""

            dm = await utils.force_say(message, ctx.bot.whisper)

            data = {
                'ctx': ctx,
                'user': ctx.message.author,
                'channel': dm.channel,
            }

            while True:
                done_extras, new_extras = await self.db_update_loop(ctx, data, session, user, done_extras, new_extras)
        finally:
            shared.state.unlock(ctx)

    async def db_update_loop(self, ctx, data, session, user, done_extras, new_extras):
        message_raw = await self.db_wait_message(data)
        message = message_raw.content

        if message in ['!quit', 'done']:
            session.commit()
            await data['ctx'].bot.add_reaction(message_raw, shared.reaction_ok)
            raise asyncio.CancelledError
        else:
            try:
                id = int(message)
            except:
                id = None

            if id is not None:
                for done in done_extras:
                    if done['extra'].id == id:
                        done_extras.remove(done)
                        new = await self.ask_extra(data, session, user, done['extra'], previous=done['user'])
                        done_extras.append({'extra': done['extra'], 'user': new})
                        await ctx.bot.whisper('Saved! To answer another question, simply type its identifier.')
                        return done_extras, new_extras

                for new in new_extras:
                    if new.id == id:
                        new_extras.remove(new)
                        user_extra = await self.ask_extra(data, session, user, new)
                        done_extras.append({'extra': new, 'user': user_extra})
                        await ctx.bot.whisper('Saved! To answer another question, simply type its identifier.')
                        return done_extras, new_extras

            await data['ctx'].bot.whisper('Invalid ID')
        return done_extras, new_extras

    @commands.command(name='_internal_extras_setup', pass_context=True, hidden=True)
    @checks.is_banned(permission=checks.PermissionLevel.UserData)
    async def db_setup(self, ctx):
        await shared.state.lock_user(ctx, '!user extras setup')

        try:
            session = database.new_session()
            user = await self.get_user(ctx, session, ctx.message.author.id)

            extras = session.query(database.Extras).all()
            user_extras = session.query(database.UserExtras).filter(database.UserExtras.user_id == user.id).all()

            if len(extras) == 0:
                await ctx.bot.whisper('No extras available')
                return

            done_extras, new_extras = self.sort_extras(extras, user_extras)

            if len(new_extras) == 0:
                await ctx.bot.whisper('You\'ve already answered all extra questions. To edit them, use `!extras update`.')
                return

            dm = await ctx.bot.whisper("""I will now ask you some random questions.
If you do not want to answer a question, simply type `-` and I will skip it.
If possible answers are specified, you can only use one of them. Otherwise, you're free to write what you want.
If at any point you want to stop answering these questions, type `!quit`.
""")

            data = {
                'ctx': ctx,
                'user': ctx.message.author,
                'channel': dm.channel,
            }

            for item in new_extras:
                await self.ask_extra(data, session, user, item)

            await ctx.bot.whisper('Annnnnnd done! Thank you! You can use `!profile extras [user]` to view other people\'s answers.')
        finally:
            shared.state.unlock(ctx)

    ###############################
    ### UTILS
    ###############################

    async def ask_extra(self, data, session, user, extra, previous=None):
        options = list(map(lambda x: x.strip().lower(), extra.options.split(','))) if extra.options else None

        while True:
            message_raw = await self.db_ask(data, extra, previous)
            message = message_raw.content

            if message == '!quit':
                session.commit()
                await data['ctx'].bot.add_reaction(message_raw, shared.reaction_ok)
                raise asyncio.CancelledError
            elif message == '-':
                if previous:
                    session.delete(previous)
                    session.commit()
                return None
            else:
                if options:
                    if message.lower() in options:
                        if previous:
                            session.delete(previous)

                        new_user_extra = database.UserExtras(user_id=user.id, extras_id=extra.id, response=message)
                        session.add(new_user_extra)
                        session.commit()
                        return new_user_extra
                    else:
                        await data['ctx'].bot.whisper('Invalid response, please choose from the specified list.')
                else:
                    if previous:
                        session.delete(previous)

                    new_user_extra = database.UserExtras(user_id=user.id, extras_id=extra.id, response=message)
                    session.add(new_user_extra)
                    session.commit()
                    return new_user_extra

    async def db_ask(self, data, extra, previous=None):
        question = extra.question
        if extra.options:
            question += f'\nPossible answers: {extra.options}'
        if previous:
            question += f'\n*Current answer:* {previous.response}'

        return await self.db_ask_raw(data, question)

    async def db_ask_raw(self, data, question):
        await data['ctx'].bot.whisper(question)
        return await self.db_wait_message(data)

    async def db_wait_message(self, data):
        message = await data['ctx'].bot.wait_for_message(author=data['user'], channel=data['channel'], timeout=self.timeout)
        if message is None:
            username = data['user'].name
            await data['ctx'].bot.whisper(f'_Dear diary, today I\'ve been completely ignored by {username}. I\'ve never felt so good!_\n[This means the command has timed out, you need to start it again to continue]')
            raise asyncio.TimeoutError
        return message

    def sort_extras(self, extras, user_extras):
        lookup = {}
        for item in user_extras:
            lookup[item.extras_id] = item

        done_extras, new_extras = [], []
        for extra in extras:
            if extra.id in lookup:
                done_extras.append({'extra': extra, 'user': lookup[extra.id]})
            else:
                new_extras.append(extra)
        return done_extras, new_extras

    async def get_user(self, ctx, session, user_id):
        user = session.query(database.User).filter(database.User.discord_id == user_id).first()
        if user is None:
            await ctx.bot.whisper(f'Hello {ctx.message.author.name}, your profile doesn\'t exist yet. Please run `!user setup` to get started!')
            raise errors.BadArgument('No profile')
        return user

def setup(bot):
    bot.add_cog(UserdbExtras(bot))
