#!/usr/bin/env python3

import asyncio
import discord
import pycountry
import glob
import re
import traceback
import subprocess
import os, sys
import datetime
from discord import enums
from discord.ext import commands

from commands import userdb, background, mal
from utils import database, shared, checks, utils, bot

class Admin:
    def __init__(self, bot):
        self.bot = bot
        self.timeout = 3600

    async def on_ready(self):
        if utils.read_property('restarting', False):
            utils.write_property('restarting', False)
            channel = self.bot.get_channel(utils.read_property('restarting_channel', None))
            previous_time = datetime.datetime.fromtimestamp(utils.read_property('restarting_time'))
            seconds = (datetime.datetime.now() - previous_time).total_seconds()
            await self.bot.send_message(channel, f'Restarted successfully in {round(seconds)} seconds.')

    async def on_socket_response(self, jsonmsg):
        if jsonmsg['t'] == 'MESSAGE_REACTION_ADD':
            # handle admin reaction on bot message
            if jsonmsg['d']['user_id'] == shared.admin:
                # emoji is there, check it and only this one
                if 'emoji' in jsonmsg['d']:
                    should_delete = jsonmsg['d']['emoji']['name'] == shared.reaction_ko
                else:
                    should_delete = False

                message = await self.bot.get_message(self.bot.get_channel(jsonmsg['d']['channel_id']), jsonmsg['d']['message_id'])
                if message.author == self.bot.user:
                    # emoji was not specified, and there is no way to know who added an emoji, so any will do
                    if not should_delete:
                        for reaction in message.reactions:
                            if reaction.emoji == shared.reaction_ko:
                                should_delete = True

                    if should_delete:
                        await self.bot.delete_message(message)

    async def on_command_error(self, error, ctx):
        try:
            print(error)

            if not isinstance(ctx.message, bot.SubcommandMessage):
                if isinstance(error, commands.errors.CommandNotFound):
                    await ctx.bot.add_reaction(ctx.message, shared.reaction_notfound)
                elif isinstance(error, commands.errors.CheckFailure):
                    await ctx.bot.add_reaction(ctx.message, shared.reaction_forbidden)
                elif isinstance(error, commands.errors.BadArgument) or isinstance(error, commands.errors.MissingRequiredArgument):
                    await ctx.bot.add_reaction(ctx.message, shared.reaction_ko)

        except Exception as e:
            print(e)

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def shutdown(self, ctx):
        if shared.state.users_in_command:
            raise commands.errors.CheckFailure()
        await ctx.bot.logout()

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def update(self, ctx, arg: str = None):
        if shared.state.users_in_command and arg != 'force':
            await ctx.bot.say('There are user commands running...')
            raise commands.errors.CheckFailure()

        verbose = arg and arg in ['-v', 'verbose']
        await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)
        time = datetime.datetime.now(datetime.timezone.utc)

        pull = subprocess.run(['git', 'pull'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf8')
        output = f'```{pull.stdout}```'
        print(pull.stdout)

        if verbose:
            await ctx.bot.say(output if len(output) < 2000 else f'Returned {pull.returncode}')

        if 0 == pull.returncode:
            utils.write_properties([
                ('restarting', True),
                ('restarting_channel', ctx.message.channel.id),
                ('restarting_time', time.timestamp())
            ])

            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            await ctx.bot.remove_reaction(ctx.message, shared.reaction_ok, self.bot.user)
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ko)

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def restart(self, ctx, arg: str = None):
        if shared.state.users_in_command and arg != 'force':
            await ctx.bot.say('There are user commands running...')
            raise commands.errors.CheckFailure()

        await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)
        os.execl(sys.executable, sys.executable, *sys.argv)


    @commands.command(pass_context=True, hidden=True, rest_is_raw=True)
    @checks.is_owner()
    async def newgame(self, ctx, *, name: str = None):
        if not name:
            game = background.get_random_game()
        else:
            game = discord.Game(name=name.strip(), type=0)

        shared.enable_bg_game_rotation = True
        utils.write_property('enable_bg_game_rotation', True)
        await ctx.bot.change_presence(game=game)

    @commands.command(pass_context=True, hidden=True, rest_is_raw=True)
    @checks.is_owner()
    async def setgame(self, ctx, type: str, *, name: str):
        trueType = {'0': 0, 'playing': 0,
                    '1': 1, 'streaming': 1,
                    '2': 2, 'listening': 2,
                    '3': 3, 'watching': 3}.get(type.lower(), 0)
        game = discord.Game(name=name.strip(), type=trueType)

        shared.enable_bg_game_rotation = False
        utils.write_property('enable_bg_game_rotation', False)
        await ctx.bot.change_presence(game=game)

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def clearcache(self, ctx):
        shared.cache.clear()
        await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)

    @commands.command(pass_context=True)
    @checks.is_banned(permission=checks.PermissionLevel.UserData)
    async def updatelist(self, ctx, target: str = None):
        if target:
            name = await utils.require_mal_username(ctx, await utils.convert_member(ctx, target))
        else:
            name = await utils.require_mal_username(ctx, ctx.message.author)

        if name:
            alist = await shared.cache.require_entity_list(ctx, name, entity='anime', force_reload=True)
            mlist = await shared.cache.require_entity_list(ctx, name, entity='manga', force_reload=True)
            if alist and mlist:
                await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)
                return
        await ctx.bot.add_reaction(ctx.message, shared.reaction_ko)

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def admin(self, ctx):
        dm = await ctx.bot.whisper('Starting interactive mode... (type `?quit` to quit)')

        data = {
            'ctx': ctx,
            'user': ctx.message.author,
            'channel': dm.channel,
        }

        channel = await self.pick_server_channel(ctx, data)
        if channel:
            await ctx.bot.whisper(f'Interactive mode in {channel.name} ({channel.server.name}): (type `?quit` to quit, `?chan` to switch channels)')
            while True:
                message = await self.wait_message(data)
                if message == '?quit':
                    await ctx.bot.whisper('Stopping interactive mode...')
                    return

                if message == '?chan':
                    channel = await self.pick_channel(ctx, data, channel.server)
                    await ctx.bot.whisper(
                        f'Interactive mode in {channel.name} ({channel.server.name}): (type `?quit` to quit, `?chan` to switch channels)')
                else:
                    await ctx.bot.send_message(channel, message)

    async def pick_server_channel(self, ctx, data):
        message = ''
        for serv in ctx.bot.servers:
            message += f'{serv.name} ({serv.id})\n'

        while True:
            server_name = await self.whisper_ask(data, f'Select a server:\n{message}')
            if server_name == '?quit':
                await ctx.bot.whisper('Stopping interactive mode...')
                return None

            server = next((x for x in ctx.bot.servers if x.id == server_name), None)
            if server:
                return await self.pick_channel(ctx, data, server)

    async def pick_channel(self, ctx, data, server):
        message = ''
        for channel in server.channels:
            if channel.type != enums.ChannelType.voice:
                message += f'{channel.name} ({channel.id})\n'

        while True:
            channel_name = await self.whisper_ask(data, f'Select a channel:\n{message}')
            if channel_name == '?quit':
                await ctx.bot.whisper('Stopping interactive mode...')
                return None

            channel = next((x for x in server.channels if x.id == channel_name), None)
            if channel:
                return channel

    async def whisper_ask(self, data, question):
        await data['ctx'].bot.whisper(question)
        return await self.wait_message(data)

    async def wait_message(self, data):
        message = await data['ctx'].bot.wait_for_message(author=data['user'], channel=data['channel'], timeout=self.timeout)
        if message is None:
            await data['ctx'].bot.whisper(f'_Timed out_')
            raise asyncio.TimeoutError
        return message.content

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def say(self, ctx, *, message = None):
        if message:
            await ctx.bot.say(message)

    @commands.command(pass_context=True, hidden=True, aliases=['for'])
    @checks.is_owner()
    async def foreach(self, ctx, n: int, *, command):
        message = ctx.message
        message.content = command
        for i in range(0, n):
            await ctx.bot.process_commands(message)

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def avatar(self, ctx):
        run_avatar_script()
        await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def ignorenickname(self, ctx, member_raw, value = 'true'):
        member = await utils.convert_member(ctx, member_raw)
        new_value = True if value.lower() in ['true', 'yes'] else False
        shared.name_restriction[member.id] = new_value
        utils.write_property('name_restriction', shared.name_restriction)
        await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)

    @commands.command(pass_context=True, hidden=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def whois(self, ctx, member_raw):
        member = await utils.convert_member(ctx, member_raw)
        lookup = utils.UserLookup(ctx.bot)

        message = f"""MAL name: {_user_get_mal_name(lookup, member)}
Discord name: {getattr(member, "name", None)}
Discord nick: {getattr(member, "nick", None)}
Display name (with ctx): {lookup.display_name_with_context(ctx, member)}
Display name (from mal): {lookup.display_name_from_mal(_user_get_mal_name(lookup, member))}"""
        await ctx.bot.say(message)

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def botstate(self, ctx):
        user_lookup = utils.UserLookup(ctx.bot)
        state = shared.state.users_in_command
        if state:
            message = ''
            for identifier, command in state.items():
                message += f'{user_lookup.display_name_from_id(identifier)}: `{command}`\n'
            await ctx.bot.say(message)
        else:
            await ctx.bot.say('No user command running')

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def clearbotstate(self, ctx):
        shared.state.users_in_command = {}
        await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)

    @commands.command(pass_context=True, hidden=True, rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def exec(self, ctx, *, commands):
        all_commands = commands.split(';;')
        for content in all_commands:
            command = bot.SubcommandMessage(message=ctx.message)
            command.content = content.strip()
            await self.bot.process_commands(command)

    @commands.command(pass_context=True, hidden=True, rest_is_raw=True)
    @checks.is_owner()
    async def setmalembed(self, ctx, *, template):
        template = template.strip(' `')
        utils.write_property('mal_embed_template', template)
        await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def bans(self, ctx):
        message = f'Banned members: {len(shared.banlist)}\n'

        user_lookup = utils.UserLookup(ctx.bot)
        for member in shared.banlist.keys():
            message += f'{user_lookup.display_name_from_id(member)} - {shared.banlist[member]}\n'
        message += '\n'

        message += 'Ban values:\n'
        for name, value in checks.PermissionLevel.__members__.items():
            message += f'{name}: {value.value}\n'

        await ctx.bot.say(message)

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def ban(self, ctx, member_raw, level: int = 0):
        member = await utils.convert_member(ctx, member_raw)
        shared.banlist[member.id] = level
        utils.write_property('banlist', shared.banlist)
        await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def unban(self, ctx, member_raw):
        member = await utils.convert_member(ctx, member_raw)
        if member.id in shared.banlist:
            shared.banlist.pop(member.id)
            utils.write_property('banlist', shared.banlist)
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)
        else:
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ko)

def _user_get_mal_name(lookup, member):
    for mal_name, discord_id in lookup.mal_table.items():
        if discord_id == member.id:
            return mal_name

def change_avatar_if_needed():
    wait_time = 3600 * 8
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    time = utils.read_property('avatar_change_time', None)

    if not time or (now - time) >= wait_time:
        utils.write_property('avatar_change_time', now)
        run_avatar_script()
        return wait_time + 1
    return wait_time - (now - time) + 1

def run_avatar_script():
    try:
        print('Attempting to run avatar update script...')
        if 0 == os.fork():
            os.execl(sys.executable, sys.executable, 'avatar.py')
    except: pass

def setup(bot):
    bot.add_cog(Admin(bot))
