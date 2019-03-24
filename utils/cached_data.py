#!/usr/bin/env python3

import asyncio
import discord
import datetime
import aiohttp
import urllib.request, json
from discord.ext import commands

from utils import database

class CachedData():
    def __init__(self):
        self.last_update = None

        self.animelists = {}
        self.anime_stats = {}

        self.mangalists = {}
        self.manga_stats = {}

        self.airing = []

    def clear(self):
        self.last_update = None
        self.animelists = {}
        self.anime_stats = {}

        self.mangalists = {}
        self.manga_stats = {}

        self.airing = []

    async def require_airing(self):
        self.check_cache_expiry()
        if self.airing:
            return self.airing

        async with aiohttp.ClientSession() as session:
            data = await self.load_api_data(session, 'http://iatgof.com/imal/airing.json')
            self.airing = data
        return self.airing

    async def preload_all(self):
        print('Preloading lists...')
        session = database.new_session()
        users = session.query(database.User).filter(database.User.mal_name.isnot(None)).all()

        for entity in ['anime', 'manga']:
            print(f'Downloading {entity} lists...')
            downloaded = self.animelists if entity == 'anime' else self.mangalists
            dl_stats = self.anime_stats if entity == 'anime' else self.manga_stats
            async with aiohttp.ClientSession() as session:
                for user in users:
                    try:
                        list = await self.load_entity_list(user.mal_name, session, entity=entity)
                        downloaded[user.mal_name] = list[entity]
                        dl_stats[user.mal_name] = list['statistics']
                    except:
                        pass

            if downloaded:
                print('Download complete')
                if entity == 'anime':
                    self.animelists = downloaded
                    self.anime_stats = dl_stats
                elif entity == 'manga':
                    self.mangalists = downloaded
                    self.manga_stats = dl_stats

        print('Preloading airing...')
        await self.require_airing()
        print('Done.')

        self.last_update = datetime.datetime.now()

    async def require_entity_lists(self, ctx, entity):
        session = database.new_session()
        users = session.query(database.User).filter(database.User.mal_name.isnot(None)).all()

        self.cleanup_cache(users)
        self.check_cache_expiry()
        if len(self.entitylists(entity)) >= len(users):
            return self.entitylists(entity)
        else:
            errors = []
            loaded = 0
            loading_message = await ctx.bot.say(f'Refreshing cached {entity}lists...')
            async with aiohttp.ClientSession() as session:
                for user in users:
                    if user.mal_name not in self.entitylists(entity):
                        try:
                            if user.mal_name:
                                list = await self.load_entity_list(user.mal_name, session, entity=entity)
                                self.set_entitylists(entity, user.mal_name, list[entity])
                                self.set_stats(entity, user.mal_name, list['statistics'])

                            loaded += 1
                            if user.mal_name:
                                await ctx.bot.edit_message(loading_message, f'Refreshing cached {entity}lists... ({loaded}/{len(users)})')
                        except Exception as e:
                            errors.append(f'Error getting {user.mal_name}\'s {entity}list: {e}')

            await ctx.bot.delete_message(loading_message)
            #if errors:
            #    await ctx.bot.edit_message(loading_message, f'Finished loading with {len(errors)} errors.\n')
            #else:
            #    await ctx.bot.edit_message(loading_message, f'Loaded {len(self.entitylists(entity))} lists.')

        self.last_update = datetime.datetime.now()
        return self.entitylists(entity)

    async def require_entity_list(self, ctx, mal_name, entity, force_reload=False):
        self.check_cache_expiry()
        if mal_name in self.entitylists(entity) and not force_reload:
            return self.entitylists(entity)[mal_name]

        async with aiohttp.ClientSession() as session:
            try:
                list = await self.load_entity_list(mal_name, session, entity=entity)
                self.set_entitylists(entity, mal_name, list[entity])
                self.set_stats(entity, mal_name, list['statistics'])
                return list[entity]
            except Exception as e:
                await ctx.bot.say(f'Error getting {mal_name}\'s {entity}list: {e}')
        return None

    def check_cache_expiry(self):
        pass
        #if self.last_update and (datetime.datetime.now() - self.last_update).total_seconds() > 86400:
            #self.animelists = {}
            #self.mangalists = {}
            #self.airing = []

    def cleanup_cache(self, users):
        lookup = {}
        for user in users:
            lookup[user.mal_name] = user

        def delete_from(alist, lookup):
            for item in list(alist.keys()):
                if not item in lookup:
                    del alist[item]

        delete_from(self.animelists, lookup)
        delete_from(self.mangalists, lookup)


    def get_entity_list(self, mal_name, entity, default=None):
        return self.entitylists(entity)[mal_name] if mal_name in self.entitylists(entity) else default

    async def load_entity_list(self, username, session, entity):
        offset = 0
        data = []
        while True:
            newdata = await self.load_api_data(session, f'https://myanimelist.net/{entity}list/{username}/load.json?status=7&offset={offset}')
            data += newdata
            if len(newdata) < 300:
                return self.translate_malapi_to_atarashii(data, entity)
            else:
                offset += len(newdata)

    async def load_api_data(self, session, url_string):
        async with session.get(url_string) as response:
            data = json.loads(await response.read())
            try:
                if 'error' in data:
                    raise Exception(data['error'])
                elif 'errors' in data:
                    raise Exception(data['errors'][0]['message'])
                else:
                    return data
            except Exception as e:
                print(e)
        raise Exception('Could not read data')

    def translate_malapi_to_atarashii(self, userlist, entity):
        def translate_item(item):
            action = 'watched' if entity == 'anime' else 'read'
            watching = 'watching' if entity == 'anime' else 'reading'
            ptw = 'plan to watch' if entity == 'anime' else 'plan to read'

            export_table = {
                f'{entity}_id': 'id',
                f'{entity}_title': 'title',
                f'{entity}_image_path': {'key': 'image_url', 'value': lambda x: x.replace('r/96x136', '')},
                f'{entity}_media_type_string': 'type',

                'anime_num_episodes': 'episodes',
                'manga_num_chapters': 'chapters',
                'manga_num_volumes': 'volumes',
                'anime_airing_status': {'key': 'status', 'value': lambda x: {1: 'currently airing', 2: 'finished airing', 3: 'not yet aired'}.get(x, '')},
                'manga_publishing_status': {'key': 'status', 'value': lambda x: {1: 'publishing', 2: 'finished', 3: 'not yet published'}.get(x, '')},

                'status': {'key': f'{action}_status', 'value': lambda x: {1: watching, 2: 'completed', 3: 'on-hold', 4: 'dropped', 6: ptw}.get(x, '')},
                'num_watched_episodes': 'watched_episodes',
                'num_read_chapters': 'chapters_read',
                'num_read_volumes': 'volumes_read',
                'score': 'score',

            }

            newitem = {'last_updated': 0}
            for previous, new in export_table.items():
                if previous in item:
                    if isinstance(new, str):
                        newitem[new] = item[previous]
                    else:
                        newitem[new['key']] = new['value'](item[previous])

            return newitem

        return {entity: list(map(translate_item, userlist)), 'statistics': {'days': 0}}

    def set_entitylists(self, entity, key, value):
        if entity == 'anime':
            self.animelists[key] = value
        elif entity == 'manga':
            self.mangalists[key] = value

    def entitylists(self, entity):
        if entity == 'anime':
            return self.animelists
        elif entity == 'manga':
            return self.mangalists
        return None

    def set_stats(self, entity, key, value):
        if entity.lower() == 'anime':
            self.anime_stats[key] = value
        elif entity.lower() == 'manga':
            self.manga_stats[key] = value
        return None

    def stats(self, entity):
        if entity.lower() == 'anime':
            return self.anime_stats
        elif entity.lower() == 'manga':
            return self.manga_stats
        return None
