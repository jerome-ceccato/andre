#!/usr/bin/env python3

import asyncio
import pytz
import datetime
import pycountry
import urllib.parse, urllib.request, json
import discord
import re
from discord.ext.commands import converter, errors
from discord import utils

from utils import database, shared


def age_from_birthdate(birthdate):
    born = datetime.datetime.strptime(birthdate, '%Y-%m-%d')
    today = datetime.date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def is_birthdate_valid(birthdate):
    if birthdate is None:
        return False
    age = age_from_birthdate(birthdate)
    return age > 10 and age < 100

def project_content(project):
    content = f'**{project.name}**: {project.description}'
    if project.link is not None:
         content += f'\n{project.link}'
    return content


def display_time_tz(rawtz):
    tz = pytz.timezone(rawtz)
    time = pytz.utc.localize(datetime.datetime.utcnow(), is_dst=None).astimezone(tz)
    return time.strftime('%H:%M:%S')


def language_display_string(code, extra, name=None):
    if not name:
        name = pycountry.languages.get(alpha_3=code).name
    if extra:
        if code.lower() == 'mis':
            return extra
        return f'{name} ({extra})'
    return name


def prog_language_display_string(name, extra):
    if extra:
        return f'{name} ({extra})'
    return name


async def require_mal_username(ctx, member):
    if member is None:
        member = ctx.message.author

    session = database.new_session()
    user = session.query(database.User).filter(database.User.discord_id == member.id).first()

    if user is None or user.mal_name is None:
        await ctx.bot.say(f'{member.name} has not set their MAL username!')
        return None
    return user.mal_name


def silent_picture_grab(mal_user):
    try:
        with urllib.request.urlopen(f'https://imal.iatgof.com/app.php/2.2/profile/{mal_user}') as url:
            data = json.loads(url.read().decode())
            return data['avatar_url']
    except:
        return None

def read_property(name, default=None):
    with open('data/properties.json') as file:
        contents = json.load(file)
        return contents[name] if name in contents else default

def write_property(name, content):
    write_properties([(name, content)])

def write_properties(items):
    try:
        with open('data/properties.json') as file:
            contents = json.load(file)
    except:
        contents = {}

    for name, content in items:
        if content is None:
            contents.pop(name, None)
        else:
            contents[name] = content
    with open('data/properties.json', 'w') as outfile:
        json.dump(contents, outfile)

async def force_say(message, say_method):
    n = 2000
    split_messages = [message[i:i+n] for i in range(0, len(message), n)]

    sent_message = None
    for msg in split_messages:
        sent_message = await say_method(msg)
    return sent_message

def to_int(s, default=0):
    try:
        return int(s)
    except:
        return default

async def safe_say(ctx, message):
    while len(message) > 2000:
        current, message = extract_chunk(message)
        await ctx.bot.say(current)
    if message:
        await ctx.bot.say(message)

def extract_chunk(message):
    chunks = ''
    while message:
        items = message.split('\n', 1)
        tmp = chunks + '\n' + items[0]
        leftover = items[1] if len(items) > 1 else ''
        if len(tmp) > 2000:
            return chunks, leftover
        chunks = tmp
        message = leftover
    return chunks, ''

class AndreMemberConverter(converter.IDConverter):
    def convert(self):
        message = self.ctx.message
        bot = self.ctx.bot
        match = self._get_id_match() or re.match(r'<@!?([0-9]+)>$', self.argument)
        server = message.server
        result = None

        # Exact discord match or ID
        if match is None:
            result = self.convert_get_from_member(server, bot, 'get_member_named')
        else:
            user_id = match.group(1)
            if server:
                result = server.get_member(user_id)
            else:
                result = converter._get_from_servers(bot, 'get_member', user_id)

        # Exact MAL match
        session = database.new_session()
        if result is None:
            result = self.convert_get_from_mal(session, server, bot, self.argument)

        # Fuzzy discord match
        if result is None:
            result = self.convert_get_from_member(server, bot, 'get_member_named_fuzzy')

        # Fuzzy MAL match
        if result is None:
            result = self.convert_get_from_mal(session, server, bot, f'%{self.argument}%')

        if result is None:
            raise errors.BadArgument('Member "{}" not found'.format(self.argument))

        return result

    def _apply_from_servers(self, bot, getter, argument):
        result = None
        for server in bot.servers:
            result = getattr(self, getter)(server, argument)
            if result:
                return result
        return result

    def convert_get_from_member(self, server, bot, method):
        if server:
            return getattr(self, method)(server, self.argument)
        else:
            return self._apply_from_servers(bot, method, self.argument)

    def convert_get_from_mal(self, session, server, bot, name_search):
        user = session.query(database.User).filter(database.User.mal_name.ilike(name_search)).first()

        if user:
            if server:
                return server.get_member(user.discord_id)
            else:
                return converter._get_from_servers(bot, 'get_member', user.discord_id)
        return None

    def get_member_named(self, server, name):
        name = name.lower()
        result = None
        members = server.members
        if len(name) > 5 and name[-5] == '#':
            potential_discriminator = name[-4:]

            result = utils.get(members, name=name[:-5], discriminator=potential_discriminator)
            if result is not None:
                return result

        def pred_exact(m):
            if m.nick:
                if name == m.nick.lower():
                    return True
            if m.name:
                if name == m.name.lower():
                    return True
            return False

        return utils.find(pred_exact, members)

    def get_member_named_fuzzy(self, server, name):
        name = name.lower()
        result = None
        members = server.members
        if len(name) > 5 and name[-5] == '#':
            potential_discriminator = name[-4:]

            result = utils.get(members, name=name[:-5], discriminator=potential_discriminator)
            if result is not None:
                return result

        def pred_fuzzy(m):
            if m.nick:
                if name in m.nick.lower():
                    return True
            if m.name:
                if name in m.name.lower():
                    return True
            return False

        return utils.find(pred_fuzzy, members)


async def convert_member(ctx, name, optional=False, print_error=True, critical_failure=True):
    try:
        return silent_convert_member(ctx, name, optional)
    except errors.BadArgument as e:
        if print_error:
            await ctx.bot.say(str(e))
        if critical_failure:
            raise e

def silent_convert_member(ctx, name, optional=False):
    if name and name.lower() == 'motsy':
        name = 'Motoko'
    if name and name.lower() == '@me':
        return ctx.message.author

    if name:
        return AndreMemberConverter(ctx, name).convert()
    elif optional:
        return None
    else:
        raise errors.BadArgument('No member specified')

class UserLookup:
    def __init__(self, bot):
        self.bot = bot

        session = database.new_session()
        users = session.query(database.User).all()
        table = {}
        for user in users:
            if user.mal_name:
                table[user.mal_name] = user.discord_id

        self.mal_table = table
        self.user_id_cache = {}

    @staticmethod
    def display_name_with_context(ctx, member):
        if member:
            return UserLookup._name_for_user(member)
        return UserLookup._name_for_user(ctx.message.author)

    def display_name_from_id(self, id):
        user = self._user_from_id(id)
        if user:
            return self._name_for_user(user)
        else:
            for mal_name, discord_id in self.mal_table.items():
                if discord_id == id:
                    return mal_name
        return None

    @staticmethod
    def display_name_from_user(user):
        return UserLookup._name_for_user(user)

    def display_name_from_mal(self, mal_name):
        if mal_name in self.mal_table:
            user = self._user_from_id(self.mal_table[mal_name])
            if user:
                return self._name_for_user(user)
        return mal_name

    @staticmethod
    def _name_for_user(user):
        if user.id in shared.name_restriction and shared.name_restriction[user.id]:
            return getattr(user, 'name', None)

        nick = getattr(user, 'nick', None)
        if nick:
            return nick
        return getattr(user, 'name', None)

    def _user_from_id(self, id):
        if id in self.user_id_cache:
            return self.user_id_cache[id]

        for member in self.bot.get_all_members():
            if member.id == id:
                self.user_id_cache[id] = member
                return member
        return None