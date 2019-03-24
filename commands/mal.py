#!/usr/bin/env python3

import asyncio
import discord
import datetime
import random
import html2text
import urllib.parse, urllib.request, json
from decimal import Decimal
from statistics import mean
from discord.ext import commands
from babel.dates import format_timedelta

from commands import userdb
from utils import database, shared, utils, checks

class MAL:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, aliases=['MAL'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def mal(self, ctx, member_raw: str = None):
        member = await utils.convert_member(ctx, member_raw, optional=True)
        mal_name = await utils.require_mal_username(ctx, member)
        if not mal_name:
            return

        true_name = utils.UserLookup.display_name_with_context(ctx, member)
        display_name = f'{true_name} - {mal_name}' if true_name and true_name.lower() != mal_name.lower() else mal_name

        message = discord.Embed(title=display_name)
        message.colour = 0x2E51A2

        embed_format = utils.read_property('mal_embed_template', default=shared.mal_embed_link_template)
        message.set_image(url=embed_format.replace('<username>', mal_name))

        description = f'Profile: <https://myanimelist.net/profile/{mal_name}>\n'

        for entity in ['anime', 'manga']:
            description += f'{entity.title()}list (<https://myanimelist.net/{entity}list/{mal_name}>)\n'

            if shared.cache.get_entity_list(mal_name, entity):
                user = make_maluser(mal_name, entity)
                description += '\n'
                for status, items in user.foreach_status():
                    description += f'*{status}:* {len(items)}\n'
                description += '\n*Mean score* {0:.2f}\n'.format(user.mean_score)
                description += f'*Days* {user.days}\n\n'

        message.description = description
        await ctx.bot.say(embed=message)

    @commands.command(pass_context=True, aliases=['SAO'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def sao(self, ctx, member_raw: str = None):
        member = await utils.convert_member(ctx, member_raw, optional=True)
        mal_name = await utils.require_mal_username(ctx, member)
        if not mal_name:
            return

        true_name = utils.UserLookup.display_name_with_context(ctx, member)
        alist = await shared.cache.require_entity_list(ctx, mal_name, entity='anime')
        if alist:
            sao_entries = []
            for anime in alist:
                if 'Sword Art Online' in anime['title']:
                    sao_entries.append(anime)

            if sao_entries:
                message = ''
                for anime in sao_entries:
                    message += f'**{anime["title"]}** ({anime["id"]}): '
                    if 'score' in anime and anime['score'] > 0:
                        message += f'{anime["score"]}'
                        if anime['watched_status'] != 'completed':
                            message += f' ({anime["watched_status"]})'
                    elif anime['watched_status'] == 'completed':
                        message += f'Completed'
                    else:
                        message += f' {anime["watched_status"]}'
                    message += '\n'
                await ctx.bot.say(f'{true_name}\'s SAO tasts:\n\n{message}')
            else:
                await ctx.bot.say(f'{true_name} has never seen SAO.')

    @commands.command(pass_context=True, aliases=['Search'], rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def search(self, ctx, entity: str = 'anime', *, name: str = None):
        entity, name = extract_optional_entity(entity, name)

        if not name:
            raise commands.errors.BadArgument()
        results = await api_load_json(ctx, f'{entity}/search?q=' + urllib.parse.quote_plus(name))
        if not results:
            await ctx.bot.say(f'No match for {name}')
            return

        message = ''
        for item in results[:10]:
            message += f'`{item["id"]}`: {item["title"]} ({item["type"]})\n'

        await ctx.bot.say(message)

    @commands.command(pass_context=True, aliases=['Anime'], rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def anime(self, ctx, *, name):
        if not name:
            raise commands.errors.BadArgument()

        await self.search_entity(ctx, name, 'anime')

    @commands.command(pass_context=True, aliases=['Manga'], rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def manga(self, ctx, *, name):
        if not name:
            raise commands.errors.BadArgument()

        await self.search_entity(ctx, name, 'manga')

    async def search_entity(self, ctx, name, entity):
        lists = await shared.cache.require_entity_lists(ctx, entity)
        entity_data, from_search = await self.get_entity_from_string(ctx, name, entity)

        # Clannad/AS easter egg
        easter_egg = False
        if 'clannad' in name.lower() and entity_data['id'] in [2167, 4181]:
            easter_egg = True

        await self.display_entity(ctx, entity, entity_data, from_search, lists, easter_egg=easter_egg)

    async def get_entity_from_string(self, ctx, name, entity):
        name = name.strip()

        if name.isdigit():
            entity_data = await api_load_json(ctx, f'{entity}/{name}')
            from_search = False
        else:
            results = await api_load_json(ctx, f'{entity}/search?q=' + urllib.parse.quote_plus(name))
            if results is None:
                return
            if not results:
                await ctx.bot.say(f'No match for {name}')
                return

            entity_data = results[0]
            from_search = True
        return entity_data, from_search

    async def display_entity(self, ctx, entity, entity_data, from_search, lists, easter_egg=False):
        message = discord.Embed(title=entity_data['title'], url=f'https://myanimelist.net/{entity}/{entity_data["id"]}')
        message.set_thumbnail(url=(entity_data['image_url'] if 'image_url' in entity_data else None))

        if from_search:
            description = entity_data['synopsis']
        else:
            synopsis = html2text.html2text(entity_data['synopsis'])
            max_size = 200
            if len(synopsis) > 200:
                synopsis = synopsis[:max_size] + '...'
            description = synopsis.replace('\n', ' ')

        description += f'\n\n*Type:* {entity_data["type"]}\n'

        if entity == 'anime':
            episodes = entity_data['episodes'] if 'episodes' in entity_data and entity_data['episodes'] > 0 else None
            if episodes:
                description += f'*Episodes:* {episodes}\n'
        elif entity == 'manga':
            volumes = entity_data['volumes'] if 'volumes' in entity_data and entity_data['volumes'] > 0 else None
            if volumes:
                description += f'*Volumes:* {volumes}\n'
            chapters = entity_data['chapters'] if 'chapters' in entity_data and entity_data['chapters'] > 0 else None
            if chapters:
                description += f'*Chapters:* {chapters}\n'

        description += f'*MAL score:* {entity_data.get("members_score", "?")}\n'

        avg_score = get_entity_avg_score(ctx, entity_data, lists, entity)
        if easter_egg:
            avg_score = 10

        description += '*nulls score:* ' + ('?' if avg_score is None else '{0:.2f}'.format(avg_score)) + '\n\n'

        description += build_entity_stats(ctx, entity_data, lists, entity, easter_egg=easter_egg)

        message.description = description
        await ctx.bot.say(embed=message)

    @commands.command(pass_context=True, aliases=['When', 'start', 'Start'], rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def when(self, ctx, entity: str = 'anime', *, name: str = None):
        entity, name = extract_optional_entity(entity, name)

        if not name:
            raise commands.errors.BadArgument()

        entity_data, _ = await self.get_entity_from_string(ctx, name, entity)
        lists = await shared.cache.require_entity_lists(ctx, entity)

        message = discord.Embed(title=entity_data['title'], url=f'https://myanimelist.net/{entity}/{entity_data["id"]}')
        message.set_thumbnail(url=(entity_data['image_url'] if 'image_url' in entity_data else None))

        description = ''

        if 'start_date' in entity_data:
            if 'end_date' in entity_data:
                aired_name = 'Aired' if entity == 'anime' else 'Published'
                description = f'{aired_name} from {entity_data["start_date"]} to {entity_data["end_date"]}\n\n'
            else:
                aired_name = 'Started airing' if entity == 'anime' else 'Started publishing'
                description = f'{aired_name}: {entity_data["start_date"]}\n\n'

        user_lookup = utils.UserLookup(ctx.bot)
        items_to_display = []
        for user, list in lists.items():
            user_display_name = user_lookup.display_name_from_mal(user)

            if entity == 'anime':
                status_key = 'watched_status'
                start_key = 'watching_start'
                end_key = 'watching_end'
            else:
                status_key = 'read_status'
                start_key = 'reading_start'
                end_key = 'reading_end'

            user_data = next((x for x in list if x['id'] == entity_data['id']), None)
            if user_data and (start_key in user_data or end_key in user_data):
                key = user_data[status_key]
                item_date = None
                item_display_string = None

                if start_key in user_data:
                    if end_key in user_data:
                        item_date = user_data[end_key]
                        item_display_string = f'**{user_display_name}**: {user_data[status_key]} - {user_data[start_key]} to {user_data[end_key]} ({date_display_string_relative(user_data[end_key])})'
                    else:
                        item_date = user_data[start_key]
                        item_display_string = f'**{user_display_name}**: {user_data[status_key]} - {user_data[start_key]} ({date_display_string_relative(user_data[start_key])})'
                else:
                    item_date = user_data[end_key]
                    item_display_string = f'**{user_display_name}**: {user_data[status_key]} - {user_data[end_key]} ({date_display_string_relative(user_data[end_key])})'

                items_to_display.append((item_date, item_display_string))

        items = sorted(items_to_display, key=lambda x: x[0])
        items = map(lambda x: x[1], items)

        description += '\n'.join(items)
        message.description = description
        await ctx.bot.say(embed=message)


    @commands.command(pass_context=True, aliases=['Animelist'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def animelist(self, ctx, status, member_raw: str = None):
        statuses_map = {
            'watching': 'watching',
            'completed': 'completed',
            'on-hold': 'on-hold',
            'onhold': 'on-hold',
            'on hold': 'on-hold',
            'dropped': 'dropped',
            'ptw': 'plan to watch',
            'plan to watch': 'plan to watch',
            'planned': 'plan to watch',
            '*': '',
            'all': ''
        }
        await self.member_list(ctx, 'anime', statuses_map[status.lower()], member_raw)

    @commands.command(pass_context=True, aliases=['Mangalist'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def mangalist(self, ctx, status, member_raw: str = None):
        statuses_map = {
            'reading': 'reading',
            'completed': 'completed',
            'on-hold': 'on-hold',
            'onhold': 'on-hold',
            'on hold': 'on-hold',
            'dropped': 'dropped',
            'ptr': 'plan to read',
            'plan to read': 'plan to read',
            'planned': 'plan to read',
            '*': '',
            'all': ''
        }
        await self.member_list(ctx, 'manga', statuses_map[status.lower()], member_raw)


    async def member_list(self, ctx, entity, status, member_raw):
        member = await utils.convert_member(ctx, member_raw, optional=True)
        mal_name = await utils.require_mal_username(ctx, member)
        if not mal_name:
            return

        max_size = 2000 - len('\n[...]')

        data = await shared.cache.require_entity_list(ctx, mal_name, entity=entity)

        status_key = 'watched_status' if entity == 'anime' else 'read_status'
        entities = [a for a in data if (not status) or (a[status_key] == status)]
        if entities:
            entity_name = 'shows' if entity == 'anime' else 'manga'
            message = f'{len(entities)} shows in {utils.UserLookup.display_name_with_context(ctx, member)}\'s {status} list:\n\n'

            entities = sorted(entities, key=lambda item: item['last_updated'], reverse=True)
            for item in entities:
                if entity == 'anime':
                    if 'watched_episodes' in item and item['watched_episodes'] > 0:
                        if not 'episodes' in item or item['episodes'] == 0:
                            episodes = item['watched_episodes']
                        else:
                            episodes = f'{item["watched_episodes"]}/{item["episodes"]}'

                        if episodes:
                            part = f'**{item["title"]}**: {episodes}\n'
                        else:
                            part = f'**{item["title"]}**\n'
                    else:
                        if status in ['completed', 'plan to watch']:
                            part = f'{item["title"]}\n'
                        else:
                            part = f'**{item["title"]}**\n'
                else:
                    if 'volumes_read' in item and item['volumes_read'] > 0:
                        if not 'volumes' in item or item['volumes'] == 0:
                            volumes = item['volumes_read']
                        else:
                            volumes = f'{item["volumes_read"]}/{item["volumes"]}'

                        if volumes:
                            part = f'**{item["title"]}**: {volumes} vol.\n'
                        else:
                            part = f'**{item["title"]}**\n'
                    elif 'chapters_read' in item and item['chapters_read'] > 0:
                        if not 'chapters' in item or item['chapters'] == 0:
                            chapters = item['chapters_read']
                        else:
                            chapters = f'{item["chapters_read"]}/{item["chapters"]}'

                        if chapters:
                            part = f'**{item["title"]}**: {chapters} vol.\n'
                        else:
                            part = f'**{item["title"]}**\n'
                    else:
                        if status in ['completed', 'plan to read']:
                            part = f'{item["title"]}\n'
                        else:
                            part = f'**{item["title"]}**\n'

                if not status:
                    part = f'{part[:-1]} ({item[status_key]})\n'
                if len(message) + len(part) > max_size:
                    message += '[...]'
                    await ctx.bot.say(message)
                    return
                message += part

            await ctx.bot.say(message)
        else:
            await ctx.bot.say(f'No entry in {mal_name}\'s {status} list!')

    @commands.group(pass_context=True, aliases=['Shared'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def shared(self, ctx):
        if ctx.invoked_subcommand is None:
            message = ctx.message
            message.content = '!help shared'
            await ctx.bot.process_commands(message)

    @shared.command(pass_context=True, aliases=['anime'], rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def shared_anime(self, ctx, *, args: str = ''):
        settings = parse_arguments(args, default={'style': 'details', 'sort': 'members', 'results': '5', 'reverse': '0', 'min_members': '0'})
        functions = functions_for_style(settings['sort'], 'anime', settings)
        anime = await sorted_grouped_entities_by(ctx, 'anime', settings, sort_function=functions['sort'])
        await display_grouped_entities(ctx, anime, settings, details=functions['details'])

    @shared.command(pass_context=True, aliases=['manga'], rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def shared_manga(self, ctx, *, args: str = ''):
        settings = parse_arguments(args, default={'style': 'details', 'sort': 'members', 'results': '5', 'reverse': '0', 'min_members': '0'})
        functions = functions_for_style(settings['sort'], 'manga', settings)
        manga = await sorted_grouped_entities_by(ctx, 'manga', settings, sort_function=functions['sort'])
        await display_grouped_entities(ctx, manga, settings, details=functions['details'])

    @commands.command(pass_context=True, aliases=['nextMAL'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def nextmal(self, ctx, member_raw = None):
        member = await utils.convert_member(ctx, member_raw, optional=True)
        mal_name = await utils.require_mal_username(ctx, member)
        if not mal_name:
            return

        entity = 'anime'
        await shared.cache.require_entity_list(ctx, mal_name, entity=entity)
        data = make_maluser(mal_name, entity)
        if data.plan_to_watch:
            anime = random.choice(data.plan_to_watch)
            await self.search_entity(ctx, f'{anime["id"]}', 'anime')
        else:
            await ctx.bot.say(f'Your PTW list is empty. Go watch Clannad.')

    @commands.command(pass_context=True, rest_is_raw=True, aliases=['Scoredistribution', 'ScoreDistribution', 'sdistribution', 'scoresdistribution', 'Scoresdistribution', 'ScoresDistribution'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def scoredistribution(self, ctx, *, args: str = ''):
        settings = parse_arguments(args, default={'entity': 'anime', 'score': None, 'sort': 'percent'})
        entity = settings['entity']
        sorting = settings['sort']
        try:
            score = int(settings['score'])
        except:
            score = None

        lists = await shared.cache.require_entity_lists(ctx, entity)
        scores_list = []
        user_lookup = utils.UserLookup(ctx.bot)

        user_data = []
        for user, list in lists.items():
            user_display_name = user_lookup.display_name_from_mal(user)
            data = make_maluser(user, entity)
            user_data.append({'name': user_display_name, 'data': data})

        if score:
            score = 10 if score > 10 or score <= 0 else score
            scores_list = self.sorted_scores_for_user(score, user_data, sorting, '{1}: **{2}** ({3})')

            message = f'Users with the most **{score}** in their {entity} list:\n\n'
            for item in scores_list:
                message += f'{item}\n'

            await ctx.bot.say(message)
        else:
            display_data = []
            for i in range(10, 0, -1):
                scores_list = self.sorted_scores_for_user(i, user_data, sorting, '**{0}**: {1} (**{2}** - {3})')
                if scores_list:
                    display_data.append(scores_list[0])

            if sorting == 'amount':
                message = f'Users with the most {entity} of each score in their list:\n\n'
            elif sorting == 'percent':
                message = f'Users with the highest percentage of each score in their {entity} list:\n\n'
            else:
                message = f'Users with the most of each score in their {entity} list:\n\n'
            for item in display_data:
                message += f'{item}\n'

            await ctx.bot.say(message)

    def sorted_scores_for_user(self, score, user_data, sorting, formatter):
        scores_list = []
        for item in user_data:
            user_display_name = item['name']
            data = item['data']

            percent = len(data.scores[score]) * 100.0 / data.total_scored if data.total_scored > 0 else 0
            percent_string = '{0:.1f}%'.format(percent)

            if sorting == 'amount':
                label = formatter.format(score, user_display_name, len(data.scores[score]), percent_string)
                scores_list.append({'sorting': len(data.scores[score]), 'label': label})
            elif sorting == 'percent':
                label = formatter.format(score, user_display_name, percent_string, len(data.scores[score]))
                scores_list.append({'sorting': percent, 'label': label})
            else:
                sorting_v = (percent / 100) * len(data.scores[score])
                label = formatter.format(score, user_display_name, '{0:.2f}'.format(sorting_v), '{} - {}'.format(len(data.scores[score]), percent_string))
                scores_list.append({'sorting': sorting_v, 'label': label})

        scores_list = sorted(scores_list, key=lambda x: x['sorting'], reverse=True)
        return list(map(lambda x: x['label'], scores_list))

    @commands.command(pass_context=True, aliases=['Compare'], rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def compare(self, ctx, member1_raw, member2_raw, *, args: str = ''):
        member = await utils.convert_member(ctx, member1_raw)
        mal_name = await utils.require_mal_username(ctx, member)

        member = await utils.convert_member(ctx, member2_raw)
        mal_name2 = await utils.require_mal_username(ctx, member)

        if not mal_name or not mal_name2:
            return

        settings = parse_arguments(args, default={'entity': 'anime', 'sort': 'similar', 'results': '20', 'min_score': '1', 'max_score': '10', 'diff_score': '-1', 'group': 'true'})

        if settings['entity'] not in ['anime', 'manga'] or settings['sort'] not in ['similar', 'different'] or settings['group'] not in ['yes', 'true', 'no', 'false']:
            raise commands.errors.BadArgument()

        list1 = await shared.cache.require_entity_list(ctx, mal_name, entity=settings['entity'])
        list2 = await shared.cache.require_entity_list(ctx, mal_name2, entity=settings['entity'])

        min_score = utils.to_int(settings['min_score'], default=1)
        max_score = utils.to_int(settings['max_score'], default=10)
        diff_score = utils.to_int(settings['diff_score'], default=-1)

        shared_items = []
        lookup1 = {}
        for item in list1:
            if 'score' in item and item['score'] >= min_score and item['score'] <= max_score:
                lookup1[item['id']] = item
        for item in list2:
            if item['id'] in lookup1:
                if 'score' in item and item['score'] >= min_score and item['score'] <= max_score:
                    if diff_score < 0 or abs(item['score'] - lookup1[item['id']]['score']) == diff_score:
                        shared_items.append([lookup1[item['id']], item])

        shared_items = sorted(shared_items, key=lambda x: abs(x[0]['score'] - x[1]['score']), reverse=(settings['sort'] == 'different'))

        message = f'*{mal_name}* - *{mal_name2}*\n\n'
        results = utils.to_int(settings['results'], default=len(shared_items))

        last_diff = -100
        should_group = settings['group'] in ['yes', 'true']
        for items in (shared_items[:results] if results > 0 else shared_items):
            current_diff = abs(items[0]['score'] - items[1]['score'])
            if should_group and current_diff != last_diff:
                if last_diff != -100:
                    message += '\n'
                if current_diff == 0:
                    message += f'**{settings["entity"].title()} with the same score:**\n'
                else:
                    message += f'**{settings["entity"].title()} with a difference of {current_diff}:**\n'
            message += f'{items[0]["title"]}: **{items[0]["score"]}'
            if current_diff != 0:
                message += f' - {items[1]["score"]}'
            message += '**\n'
            last_diff = current_diff

        await ctx.bot.say(message)

    @commands.command(pass_context=True, aliases=['Unique'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def unique(self, ctx, arg1, arg2 = None, arg3 = None):
        args = [x for x in [arg1, arg2, arg3] if x is not None]

        entity = 'anime'
        member1 = ctx.message.author
        member2 = None

        if args[0] in ['anime', 'manga']:
            entity = args.pop(0)
        if not args:
            raise commands.errors.BadArgument('No member specified')
        if len(args) == 1:
            member2 = await utils.convert_member(ctx, args[0])
        elif len(args) == 2:
            member1 = await utils.convert_member(ctx, args[0])
            member2 = await utils.convert_member(ctx, args[1])

        mal_name = await utils.require_mal_username(ctx, member1)
        mal_name2 = await utils.require_mal_username(ctx, member2)

        if not mal_name or not mal_name2:
            raise commands.errors.BadArgument('Members don\'t have a specified MAL username')

        list1 = await shared.cache.require_entity_list(ctx, mal_name, entity=entity)
        list2 = await shared.cache.require_entity_list(ctx, mal_name2, entity=entity)

        unique_items = []
        lookup2 = {}
        for item in list2:
            lookup2[item['id']] = item

        for item in list1:
            if item['id'] in lookup2:
                other_item = lookup2[item['id']]
                if ('watched_status' in other_item and other_item['watched_status'] == 'plan to watch') or ('read_status' in other_item and other_item['read_status'] == 'plan to read'):
                    unique_items.append({'item': item, 'other': other_item})
            else:
                unique_items.append({'item': item})

        data = sorted(unique_items, key=lambda x: (x['item'].get('score') is not None, x['item'].get('score')), reverse=True)

        watch_verb = 'seen' if entity == 'anime' else 'read'
        ptw = 'PTW' if entity == 'anime' else 'PTR'
        message = f'{entity.title()} in **{mal_name}**\'s list that **{mal_name2}** hasn\'t {watch_verb} yet.\nIf `{ptw}` is specified, it means the {entity} is in **{mal_name2}**\'s {ptw} list\n\n'
        max_size = 2000 - len('\n[...]')

        for item in data:
            part = f'{item["item"]["title"]}: **{item["item"].get("score") or "?"}**'
            if 'other' in item:
                part += ' (PTW)'
            part += '\n'

            if len(message) + len(part) > max_size:
                message += '[...]'
                await ctx.bot.say(message)
                return
            message += part

        await ctx.bot.say(message)

    @commands.command(pass_context=True, aliases=['Affinity'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def affinity(self, ctx, member1_raw=None, member2_raw=None, entity='anime'):

        if member1_raw in ['anime', 'manga']:
            entity = member1_raw
            member1_raw = None
        if member2_raw in ['anime', 'manga']:
            entity = member2_raw
            member2_raw = None
    
        member = await utils.convert_member(ctx, member1_raw, optional=True)
        mal_name = await utils.require_mal_username(ctx, member)

        if member2_raw:
            member = await utils.convert_member(ctx, member2_raw)
            mal_name2 = await utils.require_mal_username(ctx, member)
        else:
            mal_name2 = None

        if not mal_name:
            return

        user_list = await shared.cache.require_entity_list(ctx, mal_name, entity=entity)

        if mal_name2:
            list2 = await shared.cache.require_entity_list(ctx, mal_name2, entity=entity)
            items, score = self.get_weighted_score(user_list, list2)
            message = f'Shared {entity}: **{items}**\n'
            if score is None:
                message += 'Not enough shared scores to compute affinity\n'
            else:
                message += 'Affinity: **{0:.1f}%**\n'.format(score)
            await utils.safe_say(ctx, message)
        else:
            lists = await shared.cache.require_entity_lists(ctx, entity)
            user_lookup = utils.UserLookup(ctx.bot)
            message = ''
            data = []
            for user, list in lists.items():
                if user != mal_name:
                    items, score = self.get_weighted_score(user_list, list)
                    data.append({'items': items, 'score': score, 'user': user})

            data = sorted(data, key=lambda x: (x.get('score') is not None, x.get('score')), reverse=True)
            none_newline = True
            for item in data:
                if not ('score' in item and item['score'] is not None) and none_newline:
                    message += '\n'
                    none_newline = False
                message += f'**{user_lookup.display_name_from_mal(item["user"])}**: {item["items"]} shared scores'
                if 'score' in item and item['score'] is not None:
                    message += ', **{0:.1f}%** affinity\n'.format(item['score'])
                else:
                    message += ', can\'t compute affinity\n'

            await utils.safe_say(ctx, message)

    @commands.command(pass_context=True, aliases=['Meanscores', 'meanscore', 'Meanscore'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def meanscores(self, ctx, entity='anime'):

        lists = await shared.cache.require_entity_lists(ctx, entity)
        user_lookup = utils.UserLookup(ctx.bot)

        items = []
        for user, list in lists.items():
            mal = make_maluser(user, entity)
            items.append({'user': user, 'score': mal.mean_score})

        items = sorted(items, key=lambda x: x['score'], reverse=True)
        message = ''
        for item in items:
            message += '**{0}**: {1:.2f}\n'.format(user_lookup.display_name_from_mal(item["user"]), item['score'])
        await utils.safe_say(ctx, message)

    def get_weighted_score(self, list1, list2):
        lookup1 = {}
        scores1, scores2 = [], []

        for item in list1:
            if 'score' in item and item['score'] > 0:
                lookup1[item['id']] = item
        for item in list2:
            if item['id'] in lookup1:
                if 'score' in item and item['score'] > 0:
                    scores1.append(lookup1[item['id']]['score'])
                    scores2.append(item['score'])

        try:
            if len(scores1) <= 10:
                raise Exception()
            return len(scores1), pearson(scores1, scores2) * 100
        except:
            return len(scores1), None


def pearson(x, y):
    """
    Pearson's correlation implementation without scipy or numpy.
    :param list x: Dataset x
    :param list y: Dataset y
    :return: Population pearson correlation coefficient
    :rtype: float
    """
    mx = Decimal(mean(x))
    my = Decimal(mean(y))

    xm = [Decimal(i) - mx for i in x]
    ym = [Decimal(j) - my for j in y]

    sx = [i ** 2 for i in xm]
    sy = [j ** 2 for j in ym]

    num = sum([a * b for a, b in zip(xm, ym)])
    den = Decimal(sum(sx) * sum(sy)).sqrt()

    if den == 0.0:
        raise Exception()

    return float(num / den)

def functions_for_style(style, entity, settings):
    if style == 'members':
        return {'sort': lambda x: len(x),
                'details': lambda x: f'{len(x)} members'}
    elif style == 'completed':
        def completed_anime(from_list):
            return len([x for x in from_list if x['entity'][('watched_status' if entity == 'anime' else 'read_status')] == 'completed'])

        return {'sort': lambda x: completed_anime(x),
                'details': lambda x: f'{completed_anime(x)} members'}
    elif style == 'score':
        try:
            min_members = int(settings['min_members'])
        except:
            min_members = 0

        def avg_score(from_list):
            total, score = 0, 0
            dummy_score = 100 if settings['reverse'].lower() in ['1', 'yes', 'true'] else -1
            for item in from_list:
                if item['entity']['score'] > 0:
                    total += 1
                    score += item['entity']['score']
            return score / total if total > min_members else dummy_score

        return {'sort': lambda x: avg_score(x),
                'details': lambda x: '{0:.2f}'.format(avg_score(x))}
    return None

def parse_arguments(args, default):
    for item in args.split(' '):
        parts = item.split('=')
        if len(parts) == 2:
            default[parts[0]] = parts[1]
    return default

def extract_optional_entity(entity, name):
    entity = entity.lower()
    if not entity in ['anime', 'manga']:
        if name:
            name = entity + ' ' + name
        else:
            name = entity
        entity = 'anime'
    return entity, name

def date_display_string_relative(date):
    current = datetime.datetime.strptime(date, '%Y-%m-%d')
    difference = format_timedelta(current - datetime.datetime.now(), granularity='days', locale='en_US')
    return f'{difference} ago'

async def display_grouped_entities(ctx, entities, settings, details):
    message = ''
    max_size = 2000

    try:
        max = int(settings['results'])
    except:
        max = 5
    style = settings['style']

    user_lookup = utils.UserLookup(ctx.bot) if style == 'full' else None

    entities = entities[:max] if max > 0 else entities
    for item in entities:
        part = ''
        if style == 'short':
            part = item[0]['entity']['title'] + '\n'
        elif style == 'details':
            part = f"**{item[0]['entity']['title']}**: {details(item)}\n"
        elif style == 'full':
            members = ', '.join(map(lambda x: user_lookup.display_name_from_mal(x['user']), item))
            part = f"**{item[0]['entity']['title']}**: {members} ({details(item)})\n"
        if len(message) + len(part) > max_size:
            await ctx.bot.say(message)
            return
        message += part
    await ctx.bot.say(message)

async def sorted_grouped_entities_by(ctx, entity, settings, sort_function=None):
    entities = await build_entity_map(ctx, entity)
    should_reverse = settings['reverse'].lower() in ['1', 'yes', 'true']
    return sorted(entities.values(), reverse=not should_reverse, key=sort_function)

async def build_entity_map(ctx, entity):
    lists = await shared.cache.require_entity_lists(ctx, entity)

    map_content = {}
    for user, list in lists.items():
        for item in list:
            if item['id'] not in map_content:
                map_content[item['id']] = []
            map_content[item['id']].append({'user': user, 'entity': item})
    return map_content

def get_entity_avg_score(ctx, data, lists, entity):
    mal_id = data['id']
    nb_scores = 0
    total_score = 0

    for user, list in lists.items():
        user_data = next((x for x in list if x['id'] == mal_id), None)
        if user_data:
            if 'score' in user_data and user_data['score'] > 0:
                nb_scores += 1
                total_score += user_data['score']

    return None if nb_scores == 0 else total_score / nb_scores


def build_entity_stats(ctx, data, lists, entity, easter_egg=False):
    mal_id = data['id']
    statuses = {}
    user_lookup = utils.UserLookup(ctx.bot)

    for user, list in lists.items():
        user_display_name = user_lookup.display_name_from_mal(user)

        if entity == 'anime':
            status_key = 'watched_status'
            special_statuses = ['watching', 'on-hold', 'dropped']
        else:
            status_key = 'read_status'
            special_statuses = ['reading', 'on-hold', 'dropped']

        user_data = next((x for x in list if x['id'] == mal_id), None)
        if easter_egg:
            key = user_data[status_key] if user_data else 'not in list'
            item = f'{user_display_name} (10\*)'
        elif user_data:
            key = user_data[status_key]
            if user_data[status_key] in special_statuses:
                if entity == 'anime':
                    item = f'{user_display_name} ({user_data["watched_episodes"]} eps.)'
                else:
                    if 'volumes_read' in user_data and user_data['volumes_read'] > 0:
                        item = f'{user_display_name} ({user_data["volumes_read"]} vol.)'
                    else:
                        item = f'{user_display_name} ({user_data["chapters_read"]} ch.)'
            else:
                item = f'{user_display_name}'
                if user_data['score'] > 0:
                    item += f' ({user_data["score"]}\*)'
        else:
            key = 'not in list'
            item = user_display_name

        if key in statuses:
            statuses[key].append(item)
        else:
            statuses[key] = [item]

    message = ''
    if entity == 'anime':
        sorted_st = ['watching', 'completed', 'on-hold', 'dropped', 'plan to watch', 'not in list']
    else:
        sorted_st = ['reading', 'completed', 'on-hold', 'dropped', 'plan to read', 'not in list']
    for stat in sorted_st:
        if stat in statuses:
            users = ', '.join(statuses[stat])
            message += f'**{stat.title()}**: {users}\n'
    return message


async def api_load_json(ctx, path, toedit=None):
    with urllib.request.urlopen(f'https://imal.iatgof.com/app.php/2.2/{path}') as url:
        data = json.loads(url.read().decode())
        try:
            if 'error' in data:
                if toedit:
                    await ctx.bot.edit_message(toedit, data['error'])
                else:
                    await ctx.bot.say(data['error'])
            else:
                return data
        except Exception as e:
            print(e)
            if toedit:
                await ctx.bot.edit_message(toedit, 'Could not read data')
            else:
                await ctx.bot.say('Could not read data')
    return None


def make_maluser(mal_name, entity: str):
    if entity == 'anime':
        return MALUserAnime(mal_name)
    elif entity == 'manga':
        return MALUserManga(mal_name)
    return None

class MALUser:
    def __init__(self, mal_name, entity: str):
        self.mal_name = mal_name
        self.entity = entity

        self.list = shared.cache.entitylists(entity)[mal_name]
        self.stats = shared.cache.stats(entity)[mal_name]

        self.completed = []
        self.on_hold = []
        self.dropped = []

        self.mean_score = 0
        self.scores = {}
        self.total_scored = 0
        self.days = 0.0

        self.total_entity = 0

        self.min_start_date = None

        for i in range(0, 11):
            self.scores[i] = []

    def compute_stats(self):
        total_score = 0.0
        scored = 0
        for entity in self.list:
            flat_status = entity[self._status_key()].lower().replace(' ', '_').replace('-', '_')
            getattr(self, flat_status).append(entity)

            self.set_additional_info(entity)

            self.total_entity += 1
            if entity['score'] > 0:
                total_score += entity['score']
                scored += 1
            self.scores[entity['score']].append(entity)

            if 'watching_start' in entity:
                self.min_start_date = entity['watching_start'] if not self.min_start_date else (
                    self.min_start_date if self.min_start_date < entity['watching_start'] else entity['watching_start'])
            elif 'watching_end' in entity:
                self.min_start_date = entity['watching_end'] if not self.min_start_date else (
                    self.min_start_date if self.min_start_date < entity['watching_end'] else entity['watching_end'])

        self.total_scored = scored
        self.mean_score = total_score / scored if scored > 0 else total_score
        self.days = self.stats['days']

    def set_additional_info(self, entity):
        pass

    def foreach_status(self):
        pass

    def _status_key(self):
        return ''

class MALUserAnime(MALUser):
    def __init__(self, mal_name):
        MALUser.__init__(self, mal_name, entity='anime')

        self.watching = []
        self.plan_to_watch = []
        self.total_episodes = 0

        self.compute_stats()

    def _status_key(self):
        return 'watched_status'

    def set_additional_info(self, entity):
        self.total_episodes += entity['watched_episodes']

    def foreach_status(self):
        statuses = [('watching', 'Watching'),
                    ('completed', 'Completed'),
                    ('on_hold', 'On-Hold'),
                    ('dropped', 'Dropped'),
                    ('plan_to_watch', 'Plan to Watch')]

        for status in statuses:
            yield status[1], getattr(self, status[0])

class MALUserManga(MALUser):
    def __init__(self, mal_name):
        MALUser.__init__(self, mal_name, entity='manga')

        self.reading = []
        self.plan_to_read = []
        self.total_chapters = 0
        self.total_volumes = 0

        self.compute_stats()

    def _status_key(self):
        return 'read_status'

    def set_additional_info(self, entity):
        self.total_volumes += entity['volumes_read']
        self.total_chapters += entity['chapters_read']

    def foreach_status(self):
        statuses = [('reading', 'Reading'),
                    ('completed', 'Completed'),
                    ('on_hold', 'On-Hold'),
                    ('dropped', 'Dropped'),
                    ('plan_to_read', 'Plan to Read')]

        for status in statuses:
            yield status[1], getattr(self, status[0])

def setup(bot):
    bot.add_cog(MAL(bot))
