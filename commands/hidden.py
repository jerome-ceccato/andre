#!/usr/bin/env python3

import asyncio
import discord
import random
from discord import enums
from discord.ext import commands

from commands import userdb, background, mal
from utils import database, shared, checks, utils

class Hidden:
    def __init__(self, bot):
        self.bot = bot

    async def on_message(self, message):
        if message.author != self.bot.user:
            if message.content.strip() == 'b/maturity' and random.randrange(1, 5) == 3:
                await self.maturity(message)


    async def maturity(self, message_ctx):
        content = 'no, just the maturity level in here is generally that of a 10 year old.'
        content = "".join(random.choice([k.upper(), k]) for k in content)

        await asyncio.sleep(1)
        await self.bot.send_message(message_ctx.channel, content)

def setup(bot):
    bot.add_cog(Hidden(bot))
