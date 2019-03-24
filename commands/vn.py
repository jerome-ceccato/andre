#!/usr/bin/env python3

import asyncio
import discord
import pycountry
import glob
import json
from discord.ext import commands

from commands import userdb
from utils import database, shared, checks, vndb

class VisualNovel:
    def __init__(self, bot):
        self.bot = bot
        self.vndb_connect = None
        self.vndb_static = vndb.VNDBStatic()

    def vndb_instance(self, force=False):
        if force or not self.vndb_connect:
            self.vndb_connect = vndb.VNDB(username='iatgof-andre', password='andre')
        return self.vndb_connect

    def vndb_get(self, item, fields, filters, pre_filtered=False):
        filters = self.filter_from_user_string(filters) if not pre_filtered else filters
        try:
            return self.vndb_instance().get(item, fields, filters, '')
        except:
            return self.vndb_instance(force=True).get(item, fields, filters, '')

    def replace_alias(self, name):
        return self.vndb_static.aliases.get(name.lower(), name)

    def filter_from_user_string(self, name):
        name = self.replace_alias(name.replace('"', '').strip())
        if name.isdigit():
            return f'(id={name})'
        return f'(search~"{name}")'

    def extract_options(self, name, default=None):
        tags = default or {'spoil': False, 'tags': False, 'traits': False, 'tags_option': 'cont', 'related': False, 'vns': False}
        name = name.strip()
        items = name.split(' ')
        regular_items = []
        for item in items:
            if item in ['+spoil', '+tags', '+traits', '+related', '+vns']:
                tags[item[1:]] = True
            elif item.startswith('+tags='):
                values = item[len('+tags='):].replace('regular', 'cont').replace('nsfw', 'ero')
                tags['tags'] = True
                tags['tags_option'] = values
            else:
                regular_items.append(item)

        return ' '.join(regular_items), tags

    @commands.command(pass_context=True, aliases=['vndbhelp', 'VNDB', 'VNDBHelp'], rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def vndb(self, ctx):
        await ctx.bot.say("""**Commands**:
`!vn [options] [id|name]` Displays a VN.
`!vnsearch [name]` Searches for a VN. *Alias: vns*
`!vntags [options] [id|name]` Displays a VN's tags. *Alias: vnt*
`!vncharacter [options] [id|name]` Displays a VN character. *Alias: vnc*
`!vncharactersearch [name]` Searches for a VN character. *Aliases: vnsc, vncs*
`!vncharactertraits [options] [id|name]` Displays a character's traits. *Aliases: vntc, vnct*

**Options**:
*[option]* can be any combinaison of the following options, and can be placed anywhere in the string:
`+spoil` Enables spoiler info **[PLEASE AVOID IN PUBLIC CHANNELS]**
`+tags` On !vn, also show the VN's tags
`+traits` On !vnc, also show the character's traits
`+related` On !vn, also show related VNs
`+vns` On !vnc, also show the VNs the character appears in 

`+tags` can also be modified with a list of allowed tag categories in a comma-separated list. Categories are `regular`, `nsfw` and `tech`. Defaults to regular.

Examples: ```
!vn clannad
!vnc +traits archer
!vnt +spoil fsn +tags=nsfw,tech```

**Meta commands**:
`!vndbalias set [alias] => [id|name]` Set an alias to an ID or name. Any vndb command that takes a name as an argument will try to substitute an alias first (only exact-match work)
`!vndbalias unset [alias]` Remove an existing alias
`!vndbalias list` List existing aliases""")

    @commands.command(pass_context=True, aliases=['VN'], rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def vn(self, ctx, *, name):
        name, options = self.extract_options(name)

        query = 'basic,details,stats'
        if options['tags']:
            query += ',tags'
        if options['related']:
            query += ',relations'

        items = self.vndb_get('vn', query, name)
        if items['items']:
            item = items['items'][0]
            await self.display_vn(ctx, item, options=options)
        else:
            await ctx.bot.say('Not found')

    @commands.command(pass_context=True, aliases=['VNSearch', 'vns'], rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def vnsearch(self, ctx, *, name):
        items = self.vndb_get('vn', 'basic', name)
        message = '\n'.join(map(lambda x: f'`{x["id"]}`: {x["title"]}', items['items']))

        await ctx.bot.say(message)

    @commands.command(pass_context=True, aliases=['VNTags', 'vnt'], rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def vntags(self, ctx, *, name):
        name, options = self.extract_options(name)

        items = self.vndb_get('vn', 'basic,details,tags', name)
        if items['items']:
            item = items['items'][0]
            await self.display_vn_tags(ctx, item, options=options)
        else:
            await ctx.bot.say('Not found')

    @commands.command(pass_context=True, aliases=['VNCharacter', 'vnc'], rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def vncharacter(self, ctx, *, name):
        name, options = self.extract_options(name)

        query = 'basic,details,meas'
        if options['traits']:
            query += ',traits'
        if options['vns']:
            query += ',vns'

        items = self.vndb_get('character', query, name)
        if items['items']:
            item = items['items'][0]
            await self.display_vn_character(ctx, item, options=options)
        else:
            await ctx.bot.say('Not found')

    @commands.command(pass_context=True, aliases=['VNCharacterSearch', 'vncs', 'vnsc'], rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def vncharactersearch(self, ctx, *, name):
        items = self.vndb_get('character', 'basic', name)
        message = '\n'.join(map(lambda x: f'`{x["id"]}`: {x["name"]}', items['items']))

        await ctx.bot.say(message)

    @commands.command(pass_context=True, aliases=['VNCharacterTraits', 'vnct', 'vntc'], rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def vncharactertraits(self, ctx, *, name):
        name, options = self.extract_options(name)

        items = self.vndb_get('character', 'basic,details,traits', name)
        if items['items']:
            item = items['items'][0]
            await self.display_vn_character_traits(ctx, item, options=options)
        else:
            await ctx.bot.say('Not found')



    def set_image(self, message, url):
        if url:
            message.set_thumbnail(url=url)

    async def display_vn(self, ctx, vn, options):
        message = discord.Embed(title=vn['title'], url=f'https://vndb.org/v{vn["id"]}')
        self.set_image(message, url=(vn.get('image', None) if not vn.get('image_nsfw', False) else None))

        description = ''
        if vn.get('original', None):
            description += 'Original title: {}\n'.format(vn['original'])
        if vn.get('aliases', None):
            description += 'Aliases: {}\n'.format(vn['aliases'].replace('\n', ', '))
        description += 'Length: {}\n'.format(self.vndb_static.game_length(vn['length']))
        description += '\n'

        description += 'Popularity: {}\n'.format(vn['popularity'])
        description += 'Rating: {0:.2f}\n'.format(vn['rating'])
        description += 'Votes: {}\n'.format(vn['votecount'])

        if vn.get('description', None):
            description += '\n' + self.vndb_static.purge_bbcode(vn['description'].strip()) + '\n'

        if options['related'] and vn.get('relations', None):
            description += '\n**Related**:\n'
            for item in vn['relations']:
                description += f'{item["relation"]}: {item["title"]}\n'

        if options['tags']:
            display_tags = await self.get_display_tags(vn, options)
            if display_tags:
                description += '\n' + ', '.join(display_tags)

        message.description = description
        message.set_footer(text='id: {}'.format(vn['id']))
        await ctx.bot.say(embed=message)

    async def display_vn_tags(self, ctx, vn, options):
        message = discord.Embed(title=vn['title'], url=f'https://vndb.org/v{vn["id"]}')
        self.set_image(message, url=(vn.get('image', None) if not vn.get('image_nsfw', False) else None))

        display_tags = await self.get_display_tags(vn, options)

        message.description = '\n'.join(display_tags) if display_tags else 'No tags'
        await ctx.bot.say(embed=message)

    async def get_display_tags(self, vn, options):
        display_tags = []
        if vn.get('tags', None):
            tags_data = await self.vndb_static.require_data('tags')
            for tag in vn['tags']:
                if options['spoil'] or tag[2] == 0:  # Spoil level = 0
                    if tags_data.get(str(tag[0]), None):
                        data = tags_data[str(tag[0])]
                        if data['cat'] in options['tags_option']:
                            display_tags.append({'t': data['name'], 'p': tag[1]})

        return list(map(lambda x: x['t'], sorted(display_tags, key=lambda x: x['p'], reverse=True)))

    async def display_vn_character(self, ctx, chara, options):
        message = discord.Embed(title=chara['name'], url=f'https://vndb.org/c{chara["id"]}')
        self.set_image(message, url=chara.get('image', None))

        description = self.vndb_static.gender_display_char(chara.get('gender',  ''))
        if chara.get('original', None):
            description += ' {}\n'.format(chara['original'])
        else:
            description += '\n'
        if chara.get('aliases', None):
            description += 'Aliases: {}\n'.format(chara['aliases'].replace('\n', ', '))

        description += '\n'

        if chara.get('bloodt', None):
            description += 'Blood type: {}\n'.format(chara['bloodt'].upper())
        if chara.get('birthday', None):
            description += 'Birthday: {}\n'.format(self.vndb_static.birthday_display_string(chara['birthday']))
        measurements = self.vndb_static.measurements_display_string(chara)
        if measurements:
            description += measurements + '\n'

        if chara.get('description', None):
            description += '\n' + self.vndb_static.purge_bbcode(chara['description'].strip(), spoiler=options['spoil']) + '\n'

        if options['vns'] and chara.get('vns', None):
            description += '\n**VNs**:\n'
            for item in chara['vns']:
                if options['spoil'] or item[2] == 0:
                    vndata = self.vndb_get('vn', 'basic', f'(id={item[0]})', pre_filtered=True)
                    description += f'{vndata["items"][0]["title"]} ({item[3]})\n'

        if options['traits']:
            traits = await self.get_display_traits(chara, options)
            if traits:
                description += f'\n{traits}'

        message.description = description
        message.set_footer(text='id: {}'.format(chara['id']))
        await ctx.bot.say(embed=message)

    async def display_vn_character_traits(self, ctx, chara, options):
        message = discord.Embed(title=chara['name'], url=f'https://vndb.org/c{chara["id"]}')
        self.set_image(message, url=chara.get('image', None))

        description = await self.get_display_traits(chara, options)

        message.description = description
        await ctx.bot.say(embed=message)

    async def get_display_traits(self, chara, options):
        if chara.get('traits', None):
            raw_table = {}
            traits_data = await self.vndb_static.require_data('traits')
            for trait in chara['traits']:
                if options['spoil'] or trait[1] == 0:
                    data = traits_data.get(str(trait[0]), None)
                    if data:
                        def deep_parent_list(item):
                            queue = [item]
                            output = set()
                            while queue:
                                data = traits_data.get(queue[0], None)
                                if data:
                                    if data['parents']:
                                        queue.extend(data['parents'])
                                    else:
                                        output.add(queue[0])
                                queue.pop(0)
                            return list(output)

                        main_parents = deep_parent_list(str(trait[0]))
                        for parent in main_parents:
                            if parent not in raw_table:
                                raw_table[parent] = []
                            raw_table[parent].append(str(trait[0]))

            if raw_table:
                messages = []
                for parent, items in raw_table.items():
                    message = '**{}**: '.format(traits_data.get(parent, {'name': 'Unknown'})['name'])
                    message += ', '.join(map(lambda x: traits_data.get(x, {'name': '?'})['name'], items))
                    messages.append(message)
                return '\n'.join(messages)

        return None


    ### Meta

    @commands.group(pass_context=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def vndbalias(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.bot.say("""`!vndbalias set [alias] => [id|name]` Set an alias to an ID or name. Any vndb command that takes a name as an argument will try to substitute an alias first (only exact-match work)
`!vndbalias unset [alias]` Remove an existing alias
`!vndbalias list` List existing aliases""")

    @vndbalias.command(pass_context=True, rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Unsafe)
    async def set(self, ctx, *, raw):
        items = raw.split('=>')
        if items and len(items) == 2:
            self.vndb_static.aliases[items[0].strip().lower()] = items[1].strip()
            self.vndb_static.synchronize_aliases()
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)
        else:
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ko)

    @vndbalias.command(pass_context=True, rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Unsafe)
    async def unset(self, ctx, *, raw):
        alias = raw.strip().lower()
        if alias in self.vndb_static.aliases:
            self.vndb_static.aliases.pop(alias)
            self.vndb_static.synchronize_aliases()
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)
        else:
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ko)

    @vndbalias.command(pass_context=True, rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def list(self, ctx, *, raw):
        message = ''
        for alias, name in self.vndb_static.aliases.items():
            message += f'**{alias}**: {name}\n'
        await ctx.bot.say(message)

    ### API

    @commands.command(pass_context=True)
    async def vndbapi(self, ctx, identifier):
        success = False
        try:
            if identifier.isdigit():
                items = self.vndb_get('character', 'basic,details,vns', f'(id={identifier})', pre_filtered=True)
                if items['items']:
                    chara = items['items'][0]
                    output = {}

                    output['id'] = chara['id']
                    output['name'] = chara['name']
                    output['image'] = chara['image']
                    output['description'] = self.vndb_static.purge_bbcode(chara['description'].strip(), spoiler=False)

                    output['vns'] = []
                    if chara.get('vns', None):
                        for item in chara['vns']:
                            if item[2] == 0:
                                vndata = self.vndb_get('vn', 'basic', f'(id={item[0]})', pre_filtered=True)
                                output['vns'].append({'id': item[0], 'name': vndata["items"][0]["title"], 'role': item[3]})

                    message = f'```{json.dumps(output)}```'
                    await ctx.bot.say(message)
                    success = True
        except:
            pass

        if not success:
            await ctx.bot.say('```{"error": "not found"}```')


def setup(bot):
    bot.add_cog(VisualNovel(bot))
