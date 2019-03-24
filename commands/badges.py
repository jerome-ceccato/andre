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
from discord.ext.commands import errors

from commands import userdb, background, mal
from utils import database, shared, checks, utils, image_utils

class Badges:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True, aliases=['badgedb'])
    @checks.is_owner()
    async def badgesdb(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.bot.say("""Usage:

`!badgesdb list` lists the existing badges
`!badgesdb count` prints the number of existing badges
`!badgesdb add [description] [=> link]` adds a badge to the db. If *=>* is present, what follows is link to the badge image (its filename without the extension)
`!badgesdb edit [id] [description [=> link]]` edits an existing badge
`!badgesdb rm [id]` removes the specified badge

`!badgesdb assign [id] [member]+` Adds a badge to some members
`!badgesdb revoke [id] [member]+` Removes a badge from some members""")

    @badgesdb.command(pass_context=True)
    @checks.is_owner()
    async def list(self, ctx):
        session = database.new_session()
        badges = session.query(database.Badge).all()

        message = ''
        for badge in badges:
            link = f' ({badge.link})' if badge.link else ''
            message += f'**{badge.id}** - {badge.description}{link}\n'

        await utils.safe_say(ctx, message)

    @badgesdb.command(pass_context=True)
    @checks.is_owner()
    async def count(self, ctx):
        session = database.new_session()
        badges = session.query(database.Badge).count()

        message = f'There are {badges} unique badges available.'

        await ctx.bot.say(message)

    @badgesdb.command(pass_context=True)
    @checks.is_owner()
    async def add(self, ctx, *, raw):
        parts = raw.split('=>')

        description = parts[0].strip()
        session = database.new_session()
        new_badge = database.Badge(description=description)

        if len(parts) > 1:
            link = parts[1].strip()
            new_badge.link = link

        session.add(new_badge)
        session.commit()

        await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)

    @badgesdb.command(pass_context=True, aliases=['update'])
    @checks.is_owner()
    async def edit(self, ctx, id, *, raw):
        session = database.new_session()
        badge = session.query(database.Badge).filter(database.Badge.id == id).first()

        if badge:
            parts = raw.split('=>')

            description = parts[0].strip()
            badge.description = description

            if len(parts) > 1:
                link = parts[1].strip()
                badge.link = link
            else:
                badge.link = None

            session.commit()

            await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)
        else:
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ko)

    @badgesdb.command(pass_context=True, aliases=['remove'])
    @checks.is_owner()
    async def rm(self, ctx, id):
        session = database.new_session()
        badge = session.query(database.Badge).filter(database.Badge.id == id).first()

        if badge:
            user_badges = session.query(database.UserBadge).filter(database.UserBadge.badge_id == badge.id).all()
            for item in user_badges:
                session.delete(item)

            session.delete(badge)
            session.commit()
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)
        else:
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ko)

    def get_user(self, ctx, session, raw):
        member = utils.silent_convert_member(ctx, raw, optional=False)
        user = session.query(database.User).filter(database.User.discord_id == member.id).first()
        if not user:
            raise errors.BadArgument(f'{raw} not found')
        return user

    @badgesdb.command(pass_context=True, rest_is_raw=True)
    @checks.is_owner()
    async def assign(self, ctx, id: int, *, member_raws: str):
        session = database.new_session()
        session.autoflush = False

        get = lambda raw: self.get_user(ctx, session, raw)

        member_raws = member_raws.split()
        users = map(get, member_raws)

        for user in users:
            new_user_badge = database.UserBadge(user_id=user.id, badge_id=id, timestamp=int(datetime.datetime.now().timestamp()))
            session.add(new_user_badge)
        if users:
            session.commit()
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)
        else:
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ko)

    @badgesdb.command(pass_context=True, rest_is_raw=True)
    @checks.is_owner()
    async def revoke(self, ctx, id: int, *, member_raws: str):
        session = database.new_session()
        session.autoflush = False

        def get(raw):
            user = self.get_user(ctx, session, raw)
            user_badge = session.query(database.UserBadge).filter(database.UserBadge.user_id == user.id, database.UserBadge.badge_id == id).first()
            if not user_badge:
                raise errors.BadArgument(f'{raw} doesn\'t have this badge')
            return user_badge


        member_raws = member_raws.split()
        user_badges = map(get, member_raws)

        for user_badge in user_badges:
            session.delete(user_badge)
        if user_badges:
            session.commit()
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)
        else:
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ko)

    @commands.group(pass_context=True, aliases=['Badges'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def badges(self, ctx, member_raw: str = None):
        member = await utils.convert_member(ctx, member_raw, optional=True, print_error=False, critical_failure=False)
        if member is None:
            member = ctx.message.author

        session = database.new_session()
        user = session.query(database.User).filter(database.User.discord_id == member.id).first()

        if user is None:
            await ctx.bot.say(f'{member.name} has not set their profile!')
            return

        true_name = utils.UserLookup.display_name_with_context(ctx, member)
        message = f'*{true_name}\'s badges*\n\n'

        badges = session.query(database.Badge).all()
        user_badges = session.query(database.UserBadge).filter(database.UserBadge.user_id == user.id).all()

        if not badges or not user_badges:
            await ctx.bot.say(f'{true_name} has no badge.')
            return None

        lookup = {}
        for item in badges:
            lookup[item.id] = item

        sorted_badges = sorted(user_badges, key=lambda x: x.badge_id)
        for index, user_badge in enumerate(sorted_badges, start=1):
            item = lookup[user_badge.badge_id]
            message += f'**{index}.** {item.description}'
            message += '\n'

        await ctx.bot.say(message)

        image_path = self.badges_create_image_if_needed(lookup, sorted_badges)
        await ctx.bot.send_file(ctx.message.channel, image_path)

    def badges_create_image_if_needed(self, badges_lookup, sorted_badges):
        filenames = [badges_lookup[x.badge_id].link for x in sorted_badges]
        cache_name = '_'.join(filenames) + '.png'

        cache_dir = 'data/cache/'
        badges_dir = 'data/badges/'

        result_path = cache_dir + cache_name
        if os.path.isfile(result_path):
            return result_path

        image_paths = [f'{badges_dir}{f}.png' for f in filenames]
        return image_utils.create_image_composition(from_image_paths=image_paths, output_path=result_path)


def setup(bot):
    bot.add_cog(Badges(bot))
