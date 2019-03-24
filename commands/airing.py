#!/usr/bin/env python3

import asyncio
import discord
import datetime
import html2text
import traceback
import urllib.parse, urllib.request, json
from babel.dates import format_timedelta
from discord.ext import commands

from commands import userdb
from utils import database, shared, utils, checks


class Airing:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True, aliases=['Airing'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def airing(self, ctx):
        if ctx.invoked_subcommand is None:
            items = ctx.message.content.split(' ', 1)
            await self.perform_airing_action(ctx, items[1] if len(items) > 1 else None)

    @airing.command(pass_context=True, aliases=['Watching'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def watching(self, ctx, *, input: str = None):
        await self.perform_airing_action(ctx, input, watching_only=True)

    async def perform_airing_action(self, ctx, input, member_name=None, title_filter=None, watching_only=False):
        if input:
            content = input.strip().lower()
            member = await utils.convert_member(ctx, content, optional=True, critical_failure=False,
                                                print_error=False)
            if member:
                member_name = await utils.require_mal_username(ctx, member)
                if not member_name:
                    return
            else:
                title_filter = content

        if member_name:
            airing_data = AiringData(await shared.cache.require_airing(),
                                     {member_name: await shared.cache.require_entity_list(ctx, member_name, 'anime')})
        else:
            airing_data = AiringData(await shared.cache.require_airing(),
                                     await shared.cache.require_entity_lists(ctx, 'anime'))

        self_user = await utils.require_mal_username(ctx, ctx.message.author) if not member_name else None
        user_lookup = utils.UserLookup(ctx.bot)

        await utils.safe_say(ctx, self.airing_message(airing_data, user_lookup, member=member_name, title_filter=title_filter,
                                                      watching_only=watching_only, hl_self=self_user))

    def build_airing_data_member(self, data, member, title_filter):
        entities = []
        for anime in data.airing_anime:
            if (not title_filter) or title_filter in anime.users[0]["anime"]["title"].lower():
                display = None
                item = next((x for x in anime.users if x['user'].lower() == member.lower()), None)
                if item:
                    user_data = item['anime']
                    entities.append({'airing': anime, 'user_data': user_data})

        return sorted(entities, key=lambda x: x['user_data']['title'].lower())

    def build_airing_data(self, data, title_filter):
        entities = []
        for anime in data.airing_anime:
            if (not title_filter) or title_filter in anime.users[0]["anime"]["title"].lower():
                user_data_list = anime.users
                if user_data_list:
                    entities.append({'airing': anime, 'user_data': user_data_list})

        target_date = (datetime.date.today() + datetime.timedelta(1)).strftime('%Y-%m-%d')
        entities = [x for x in entities if x['user_data'][0]['anime'].get('start_date', '0000') <= target_date]
        return sorted(entities, key=lambda x: x['user_data'][0]['anime'].get('start_date', '0000'), reverse=True)

    def display_strings_for_airing_data_member(self, data, user_lookup, member, watching_only=False):
        messages = [f'{user_lookup.display_name_from_mal(member)}\'s airing list:\n\n']

        grouped_statuses = {}
        for item in data:
            display = None
            status = item['user_data']['watched_status']
            if (not watching_only) or status == 'watching':
                if status not in grouped_statuses:
                    grouped_statuses[status] = []
                grouped_statuses[status].append(item)

        def display_string_for_anime(anime, user_data, user_lookup, member):
            display = ''
            if 'watched_episodes' in user_data and user_data['watched_episodes'] > 0:
                display = f'{user_data["watched_episodes"]}'
                if user_data['watched_status'] in ['dropped', 'on-hold']:
                    plural = 's' if user_data['watched_episodes'] > 1 else ''
                    display = f'{user_data["watched_status"]} ({display} ep{plural})'
                else:
                    display += f'{anime.aired_total_string()}'
                    if 'episodes' in user_data and user_data['episodes'] > 0:
                        display += f' ({user_data["episodes"]} total)'
            else:
                display = 'PTW'
            return f'**{user_data["title"]}**: {display}\n'

        layout = ['watching', '', 'plan to watch', 'completed', '', 'on-hold', 'dropped']
        for item in layout:
            if item:
                if item in grouped_statuses:
                    messages += map(
                        lambda x: display_string_for_anime(x['airing'], x['user_data'], user_lookup, member),
                        grouped_statuses[item])
            else:
                messages.append('\n')
        return messages

    def display_strings_for_airing_data(self, data, user_lookup, watching_only=False, hl_self=None):
        messages = []

        def display_string_for_anime(anime, item, user_lookup, hl_self):
            display = ''
            user_data = item['anime']
            formatter = '`{}`' if hl_self and item["user"] == hl_self else '{}'

            user_name = user_lookup.display_name_from_mal(item["user"])
            if 'watched_episodes' in user_data and user_data['watched_episodes'] > 0:
                if user_data['watched_status'] in ['dropped', 'on-hold']:
                    display = f'{user_data["watched_episodes"]}'
                    plural = 's' if user_data['watched_episodes'] > 1 else ''
                    return formatter.format(f'{user_name} ({user_data["watched_status"]} {display} ep{plural})')
                return formatter.format(f'{user_name} ({user_data["watched_episodes"]}{anime.aired_total_string()})')
            else:
                return formatter.format(f'{user_name} (PTW)')

        for anime in data:
            grouped_statuses = {}
            for item in anime['user_data']:
                display = None
                status = item['anime']['watched_status']
                if (not watching_only) or status == 'watching':
                    if status not in grouped_statuses:
                        grouped_statuses[status] = []
                    grouped_statuses[status].append(item)

            user_statuses = []
            layout = ['watching', 'plan to watch', 'completed', 'on-hold', 'dropped']
            for item in layout:
                if item in grouped_statuses:
                    user_statuses += map(
                        lambda x: display_string_for_anime(anime['airing'], x, user_lookup, hl_self),
                        grouped_statuses[item])

            if user_statuses:
                display = ', '.join(user_statuses)
                message = f'**{anime["user_data"][0]["anime"]["title"]}**: {display}\n'
                messages.append(message)

        return messages

    def airing_message(self, data, user_lookup, member = None, title_filter = None, watching_only = False, hl_self = None):
        try:
            if member:
                data = self.build_airing_data_member(data, member, title_filter)
                messages = self.display_strings_for_airing_data_member(data, user_lookup, member, watching_only)
                return ''.join(messages)
            else:
                data = self.build_airing_data(data, title_filter)
                messages = self.display_strings_for_airing_data(data, user_lookup, watching_only, hl_self)
                return ''.join(messages)
        except Exception as error:
            print(error)
            print(traceback.format_exc())

class AiringData:
    def __init__(self, airing, lists):
        self.airing_anime = self._build_airing_anime(airing, self._build_list_map(lists))

    def _build_list_map(self, lists):
        table = {}
        for user, list in lists.items():
            for anime in list:
                if anime['id'] not in table:
                    table[anime['id']] = []
                table[anime['id']].append({'user': user, 'anime': anime})
        return table

    def _build_airing_anime(self, raw, table):
        airing = []
        for anime in raw:
            id = int(anime['mal_id'])
            if id in table:
                airing.append(AiringAnime(id, table[id], anime['airing']))
        return airing

class AiringAnime:
    def __init__(self, id, users, data):
        self.id = id
        self.users = users
        self.upcoming, self.previous = self._build_episodes(data)

    def _build_episodes(self, data):
        now = datetime.datetime.now()
        past, new = [], []
        for ep in data:
            date = datetime.datetime.fromtimestamp(ep['t'])
            if date > now:
                new.append({'n': ep['n'], 't': date})
            else:
                past.append({'n': ep['n'], 't': date})
        return new, past

    def last_aired_episode(self):
        if self.upcoming:
            return self.upcoming[0]['n'] - 1
        elif self.previous:
            return self.previous[-1]['n']
        else:
            return 0

    def aired_total_string(self):
        n = self.last_aired_episode()
        return f'/{n}' if n else ''

    def next_episode_display_string(self):
        if self.upcoming:
            ep = self.upcoming[0]
            date = format_timedelta(ep['t'] - datetime.datetime.now(), granularity='minute', locale='en_US')
            previous = ''
            if self.previous:
                prev = self.previous[-1]
                prev_date = format_timedelta(datetime.datetime.now() - prev['t'], granularity='minute', locale='en_US')
                previous = f'Last episode ({prev["n"]}) aired {prev_date} ago\n'
            return f'{previous}Next episode ({ep["n"]}) in {date}'
        return None

def setup(bot):
    bot.add_cog(Airing(bot))
