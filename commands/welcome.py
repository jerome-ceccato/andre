#!/usr/bin/env python3

import asyncio
import discord
import pycountry
import glob
from discord.ext import commands

from commands import userdb
from utils import database, shared, checks

class Welcome:
    def __init__(self, bot):
        self.bot = bot

    async def on_member_join(self, member):
        await self.welcome_member(member)

    @commands.command(pass_context=True, aliases=['Welcome'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def welcome(self, ctx, member: discord.Member):
        await self.welcome_member(member)


    async def welcome_member(self, member: discord.Member):
        server = member.server
        if member.id == shared.foxy_id:
            message = f'Hey look it\'s {member.mention} again.'
        else:
            message = f'Hello {member.mention} and welcome to {server.name}! {shared.emote_kanna}\n'
            message += """
When you're ready, you can send me `!user setup` (or type it in any channel), and I will ask you a few questions to build you a profile!
Please take a minute or two to do it \:)"""
        await self.bot.send_message(server, message)


def setup(bot):
    bot.add_cog(Welcome(bot))
