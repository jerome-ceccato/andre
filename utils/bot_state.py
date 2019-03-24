#!/usr/bin/env python3

import asyncio
import discord
import datetime
import aiohttp
import urllib.request, json
from discord.ext import commands

from utils import database

class BotState():
    def __init__(self):
        self.users_in_command = {}

    async def lock_user(self, ctx, command):
        member = ctx.message.author
        if self.user_is_in_command(member):
            await ctx.bot.whisper(f'You\'re already using the command `{self.users_in_command[member.id]}`, please quit it before running another user command.')
            raise commands.errors.DisabledCommand()
        self.user_set_command(member, command)

    def unlock(self, ctx):
        self.user_cleanup(ctx.message.author)

    def user_is_in_command(self, member):
        return member.id in self.users_in_command

    def user_set_command(self, member, command):
        self.users_in_command[member.id] = command

    def user_cleanup(self, member):
        self.users_in_command.pop(member.id)
