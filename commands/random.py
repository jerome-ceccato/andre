#!/usr/bin/env python3

import asyncio
import datetime
import discord
import json
import aiohttp
import tempfile
import subprocess, os
import random
import cexprtk
from discord.ext import commands
from discord.ext.commands import errors

from commands import userdb
from utils import checks, database, shared, utils

class Random:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, aliases=['School'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def school(self, ctx, *, grade = None):
        raw = {'3': ['Petite section de maternelle', 'Nursery', 'Nursery'],
               '4': ['Moyenne section de maternelle', 'Reception', 'Pre-K'],
               '5': ['Grande section de maternelle', 'Year 1', 'Kindergarten'],
               '6': ['CP', 'Year 2', '1st grade'],
               '7': ['CE1', 'Year 3', '2nd grade'],
               '8': ['CE2', 'Year 4', '3rd grade'],
               '9': ['CM1', 'Year 5', '4th grade'],
               '10': ['CM2', 'Year 6', '5th grade'],
               '11': ['6ème', 'Year 7', '6th grade'],
               '12': ['5ème', 'Year 8', '7th grade'],
               '13': ['4ème', 'Year 9', '8th grade'],
               '14': ['3ème', 'Year 10', '9th grade'],
               '15': ['Seconde', 'Year 11', '10th grade'],
               '16': ['Première', 'Year 12', '11th grade'],
               '17': ['Terminale', 'Year 13', '12th grade']}

        if grade is not None:
            grade = grade.lower().strip()
            for age, grades in raw.items():
                if grade in map(lambda x: x.lower(), grades) or grade == age:
                    await ctx.bot.say(f'Age: {age}\nFrance: {grades[0]}\nUK: {grades[1]}\nUSA: {grades[2]}')
                    return
        else:
            message = ''
            for age, grades in raw.items():
                message += f'Age: **{age}**, France: **{grades[0]}**, UK: **{grades[1]}**, USA: **{grades[2]}**\n'
            await ctx.bot.say(message)

    @commands.command(pass_context=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def ping(self, ctx):
        pingtime = int(round((datetime.datetime.utcnow() - ctx.message.timestamp).total_seconds() * 1000, 0))
        message = f"{pingtime} ms"
        await ctx.bot.say(message)

    @commands.command(pass_context=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def hello(self, ctx):
        await ctx.bot.say('>hello')

    @commands.command(pass_context=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def quote(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get('http://inspirobot.me/api?generate=true') as response:
                url = await response.text()

                message = discord.Embed()
                message.colour = random.randrange(0, 0xFFFFFF)
                message.set_image(url=url)
                await ctx.bot.say(embed=message)

    @commands.command(pass_context=True, rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Unsafe)
    async def bc(self, ctx, *, args):
        args = args.strip(' `')

        for banned_word in ['open', 'read', 'write', 'getline']:
            if banned_word in args:
                raise errors.CheckFailure(f'Banned word found')
        try:
            await ctx.bot.say(str(cexprtk.evaluate_expression(args, {})))
        except:
            raise errors.BadArgument(f'Invalid expression')


    @commands.command(pass_context=True, aliases=['tasts'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def _internal_reaction_picture(self, ctx):
        await ctx.bot.send_file(ctx.message.channel, f'data/assets/{ctx.invoked_with}.png')

    @commands.command(pass_context=True, aliases=['eva', 'noop', 'quit', 'meesterP', 'election', 'votes'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def _internal_aliases(self, ctx, *, args=None):
        commands = {
            'eva': '',
            'noop': '',
            'quit': '',
            'meesterP': '!exec !updatelist ;; !airing @me',
            'election': f'!say {shared.emote_humm} do you mean `b/election votes`? {shared.emote_humm}',
            'votes': f'!say {shared.emote_humm} do you mean `b/election votes`? {shared.emote_humm}'
        }

        args = f' {args}' if args else ''
        ctx.message.content = commands.get(ctx.invoked_with, '').replace('{args}', args)
        await ctx.bot.process_commands(ctx.message)


def setup(bot):
    bot.add_cog(Random(bot))
