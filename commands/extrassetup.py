#!/usr/bin/env python3

import asyncio
import discord
import pycountry
import glob
import re
import subprocess
import os, sys
import datetime
from discord import enums
from discord.ext import commands

from commands import userdb, background, mal
from utils import database, shared, checks, utils

class ExtrasSetup:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True, aliases=['extradb'])
    @checks.is_owner()
    async def extrasdb(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.bot.say("""Usage:

`!extrasdb list` lists the existing extras
`!extrasdb add [question] [=> [options]]` adds a question to the extras. If *=>* is present, what follows is a comma-separated list representing the possible options
`!extrasdb edit [id] [new_question]` edits an existing question
`!extrasdb rm [id]` removes the specified extra and all user answers""")

    @extrasdb.command(pass_context=True)
    @checks.is_owner()
    async def list(self, ctx):
        session = database.new_session()
        extras = session.query(database.Extras).all()

        message = ''
        for extra in extras:
            options = f' => {extra.options}' if extra.options else ''
            message += f'**{extra.id}** - {extra.question}{options}\n'

        await utils.safe_say(ctx, message)

    @extrasdb.command(pass_context=True)
    @checks.is_owner()
    async def add(self, ctx, *, raw):
        parts = raw.split('=>')

        question = parts[0].strip()
        session = database.new_session()
        new_extra = database.Extras(question=question)

        if len(parts) > 1:
            options = parts[1].strip()
            new_extra.options = options

        session.add(new_extra)
        session.commit()

        await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)

    @extrasdb.command(pass_context=True, aliases=['update'])
    @checks.is_owner()
    async def edit(self, ctx, id, *, raw):
        session = database.new_session()
        extra = session.query(database.Extras).filter(database.Extras.id == id).first()

        if extra:
            parts = raw.split('=>')

            question = parts[0].strip()
            extra.question = question

            if len(parts) > 1:
                options = parts[1].strip()
                extra.options = options
            else:
                extra.options = None

            session.commit()

            await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)
        else:
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ko)

    @extrasdb.command(pass_context=True, aliases=['remove'])
    @checks.is_owner()
    async def rm(self, ctx, id):
        session = database.new_session()
        extra = session.query(database.Extras).filter(database.Extras.id == id).first()

        if extra:
            user_extras = session.query(database.UserExtras).filter(database.UserExtras.extras_id == extra.id).all()
            for item in user_extras:
                session.delete(item)

            session.delete(extra)
            session.commit()
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)
        else:
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ko)

def setup(bot):
    bot.add_cog(ExtrasSetup(bot))
