#!/usr/bin/env python3

import asyncio
import discord
import re
from discord.ext import commands

from utils import shared, utils, checks, bot

class Inline:
    def __init__(self, bot):
        self.bot = bot

    async def on_message(self, message):
        if not message.author.bot and not checks.is_banned_check(message, checks.PermissionLevel.Unsafe):
            if '!!' in message.content:
                await self.process_message(message)

    async def process_message(self, message):
        content = message.content
        loops = 0

        while True:
            pos = content.find('!!')
            if pos == -1:
                return

            content = content[pos + 1:]
            end_pos = content.find('!!')
            command_content = content if end_pos == -1 else content[:end_pos]

            command = bot.SubcommandMessage(message=message)
            command.content = command_content.strip()

            await self.bot.process_commands(command)

            loops += 1
            if not checks.is_owner_check(message) and loops >= 3:
                break


def setup(bot):
    bot.add_cog(Inline(bot))
