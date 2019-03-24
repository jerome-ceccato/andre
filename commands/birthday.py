#!/usr/bin/env python3

import asyncio
import discord
import datetime
from discord.ext import commands
from utils import database, shared, utils, checks

def time_until_next_birthday():
    last_message = utils.read_property('last_birthday_check')
    if last_message:
        today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        if last_message != today:
            return 0
        else:
            now = datetime.datetime.utcnow()
            target = now.replace(hour=12, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
            return (target - now).total_seconds()
    else:
        return 0

async def check_birthdays(bot):
    print(f'checking birthdays {datetime.datetime.utcnow()}')
    utils.write_property('last_birthday_check', datetime.datetime.utcnow().strftime('%Y-%m-%d'))

    session = database.new_session()
    users = session.query(database.User).filter(database.User.birthdate.isnot(None)).all()

    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    for user in users:
        if user.birthdate[4:] == today[4:]:
            if user.discord_id not in shared.birthday_blacklist:
                if utils.is_birthdate_valid(user.birthdate):
                    await wish_birthday(bot, user)

async def wish_birthday(bot, user):
    general = bot.get_channel(shared.general_channel)
    message = f'Happy birthday <@{user.discord_id}>! {shared.emote_tada}{shared.emote_tada}{shared.emote_tada}'

    await bot.send_message(general, message)


class Birthday:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def birthday(self, ctx):
        await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)
        await check_birthdays(ctx.bot)

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def birthdaytime(self, ctx):
        await ctx.bot.say(f'Seconds until next check: {int(time_until_next_birthday())}')

def setup(bot):
    bot.add_cog(Birthday(bot))