#!/usr/bin/env python3

import asyncio
import pytz
import datetime
import pycountry
import discord
import re
from discord.ext import commands

from utils import database, utils, shared, checks

class Userdb:
    def __init__(self, bot):
        self.bot = bot
        self.timeout = 180.0
        self.questions = {
            'mal_name': 'What is your MAL username?',
            'gender': 'What is your gender?',
            'birthdate': 'When were you born? (yyyy-mm-dd)',
            'country': 'Where are you from? (country)',
            'languages': 'What languages do you speak? Make a comma-separated list with the following format:\n`name or code (optional extra info)`\nExamples: `english`, `french (learning)`, `deu`, or for exotic languages, use the special code mis and specify the language after: `mis (BSL)`',
            'prog_languages': 'What are some programming languages that you know and like?\nMake a comma-separated list, mark extra info in parenthesis. Examples: `C++ (my favourite one), Javascript (learning), WhiteSpace (weird though), Lua`',
            'bio': 'Tell me about yourself!',
            'timezone': 'What is your current timezone?\nThe timezone should look like `Region/City`. You can find your timezone here: http://www.timezoneconverter.com/cgi-bin/findzone'
        }

        self.default_values = {
            'mal_name': 'unknown',
            'gender': 'unknown',
            'birthdate': '1900-01-01',
            'country': 'United States',
            'languages': 'mis (none)',
            'prog_languages': 'none',
            'bio': 'nothing',
            'timezone': 'UTC'
        }

    @commands.group(pass_context=True, aliases=['User'])
    @checks.is_banned(permission=checks.PermissionLevel.UserData)
    async def user(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.help(ctx)

    async def help(self, ctx):
        await ctx.bot.say("""Usage:

`!user setup` starts the q/a to fill your profile
`!user update` lets you update part of your profile
`!user extras setup` starts the q/a to fill your extras profile
`!user extras update` lets you update part of your extras profile""")

    @user.group(name='extras', pass_context=True, aliases=['extra'])
    @checks.is_banned(permission=checks.PermissionLevel.UserData)
    async def db_extras(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.help(ctx)

    @db_extras.command(name='setup', pass_context=True)
    @checks.is_banned(permission=checks.PermissionLevel.UserData)
    async def db_extras_setup(self, ctx):
        message = ctx.message
        message.content = '!_internal_extras_setup'
        await ctx.bot.process_commands(message)

    @db_extras.command(name='update', pass_context=True)
    @checks.is_banned(permission=checks.PermissionLevel.UserData)
    async def db_extras_update(self, ctx):
        message = ctx.message
        message.content = '!_internal_extras_update'
        await ctx.bot.process_commands(message)

    ###############################
    ### UPDATE
    ###############################

    @user.command(name='update', pass_context=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def db_update(self, ctx):
        await shared.state.lock_user(ctx, '!user update')

        try:
            user_id = ctx.message.author.id

            session = database.new_session()
            user = session.query(database.User).filter(database.User.discord_id == user_id).first()
            if user is None:
                await ctx.bot.whisper(f'Hello {ctx.message.author.name}, your profile doesn\'t exist yet. Please run `!user setup` to get started!')
                return

            fields = ', '.join(map(lambda x: f'`{x}`', self.questions.keys()))
            fields += 'and `projects`'
            dm = await ctx.bot.whisper(f'Hello {ctx.message.author.name}, You can edit any of the following fields (just type its name, or `done` to stop updating your profile):\n{fields}')
            data = {
                'ctx': ctx,
                'user': ctx.message.author,
                'channel': dm.channel,
            }

            while True:
                response = await self.db_wait_message(data)
                response = response.lower()

                if response == 'done':
                    break

                elif response in ['mal_name', 'gender', 'bio']:
                    setattr(user, response, await self.db_ask(data, response))
                    session.commit()
                elif response in ['birthdate']:
                    setattr(user, response, await self.db_ask_date(data, response))
                    session.commit()
                elif response == 'country':
                    await self.db_fill_country(ctx, data, session, user)
                elif response == 'timezone':
                    await self.db_fill_tz(ctx, data, session, user)
                elif response == 'languages':
                    await self.db_fill_languages(ctx, data, session, user)
                elif response == 'prog_languages':
                    await self.db_fill_prog_languages(ctx, data, session, user)
                elif response == 'projects':
                    await self.update_projects(ctx, data, session, user)

                await ctx.bot.whisper( f'You can edit any of the following fields (just type its name, or `done` to stop updating your profile):\n{fields}')

            await ctx.bot.whisper(f'Thank you!')
        finally:
            shared.state.unlock(ctx)

    ###############################
    ### SETUP
    ###############################

    @user.command(name='setup', pass_context=True)
    @checks.is_banned(permission=checks.PermissionLevel.UserData)
    async def db_setup(self, ctx, arg = None):

        session = database.new_session()
        user_id = ctx.message.author.id
        user = session.query(database.User).filter(database.User.discord_id == user_id).first()

        if user is not None and arg != 'force':
            await ctx.bot.whisper(f"""You already have a profile, did you mean to edit it using `!user update`?
If you want to go through the setup again, use `!user setup force`""")
            return

        await shared.state.lock_user(ctx, '!user setup')
        try:
            dm = await ctx.bot.whisper(f"""Hello {ctx.message.author.name}, let's get started!
I'm going to ask a few questions so we can get to know you. This is just to get a general idea of who you are, it's not for the NSA, I swear.
If you don't want to answer one of these question, just type `-` and I'll ignore it or put some default value if needed.
You can edit this later using `!user update`.""")

            data = {
                'ctx': ctx,
                'user': ctx.message.author,
                'channel': dm.channel,
            }


            if user is None:
                user = database.User(discord_id=user_id)
                session.add(user)

            user.mal_name = await self.db_ask(data, 'mal_name')
            session.commit()
            user.birthdate = await self.db_ask_date(data, 'birthdate')
            session.commit()
            user.gender = await self.db_ask(data, 'gender')
            session.commit()

            await self.db_fill_country(ctx, data, session, user)
            await self.db_fill_tz(ctx, data, session, user)
            await self.db_fill_languages(ctx, data, session, user)
            await self.db_fill_prog_languages(ctx, data, session, user)
            user.bio = await self.db_ask(data, 'bio')
            session.commit()
            await self.update_projects(ctx, data, session, user)

            session.commit()
            await ctx.bot.whisper(f"""That's all for now, thank you!
You can see your profile or other people's profile by using `!profile [user]`

If you still want to tell us about you, here are some additional commands you can run:
`!user extras setup`: Lets you answer some additional random questions
`b/waifuset`: A command by BobDono to let you set your waifu

You can also run `!bots` for more info about bots, don't hesitate to play with us.
Lastly, keep an eye on the channels under ELECTIONS, we run very important waifu wars in them. Yes, this server is for Intellectuals™.

Also, please avoid using `@everyone` or `@here` unless it's a real emergency.
Instead, you should use `@AMA` if you have a question or need some help.""")

        finally:
            shared.state.unlock(ctx)

    async def update_projects(self, ctx, data, session, user):
        while True:
            if user.projects:
                projects = ', '.join(map(lambda x: x.name, user.projects))
                message = f'You have {len(user.projects)} project(s): {projects}'
            else:
                message = f'You currently have no project'
            message += f'\nYou can `add`, `update` or `remove` a project. Enter the corresponding action or `done` to stop editing projects.'
            await ctx.bot.whisper(message)
            response = await self.db_wait_message(data)
            response = response.lower()

            if response == 'done':
                return

            elif response == 'add':
                name = await self.db_ask_q(data, 'What is the name of your project?')
                project = session.query(database.Project).filter(database.Project.name.ilike(name)).first()
                if project is not None:
                    while True:
                        add_project = await self.db_ask_q(data, f'{utils.project_content(project)}\nDo you want to add this project? (yes/no)')
                        if add_project.lower() == 'yes':
                            user.projects.append(project)
                            session.commit()
                            break
                        elif add_project.lower() == 'no':
                            break
                else:
                    project = database.Project(name=name)
                    await self.edit_project_content(ctx, data, session, user, project)
                    session.add(project)
                    user.projects.append(project)
                    session.commit()

            elif response == 'update':
                name = await self.db_ask_q(data, 'What is the name of your project?')
                project = next((x for x in user.projects if x.name.lower() == name.lower()), None)
                if project is not None:
                    await self.edit_project_content(ctx, data, session, user, project)
                    session.commit()
                else:
                    await ctx.bot.whisper('Project not found.')

            elif response == 'remove':
                name = await self.db_ask_q(data, 'What is the name of your project?')
                project = next((x for x in user.projects if x.name.lower() == name.lower()), None)
                if project is not None:
                    user.projects.remove(project)
                    owner = session.query(database.User).filter(database.User.projects.any(database.Project.id == project.id)).first()
                    if owner is None:
                        session.delete(project)
                    session.commit()
                else:
                    await ctx.bot.whisper('Project not found.')

    async def edit_project_content(self, ctx, data, session, user, project):
        project.description = await self.db_ask_q(data, 'Describe your project')
        link = await self.db_ask_q(data, 'Provide a link for your project (or `-` if you have no link)')
        project.link = None if link == '-' else link

    def db_fill(self, session, user, field, class_name, content):
        if content is not None:
            setattr(user, field, self.db_fetch_or_create(session, content, class_name))
            session.commit()

    async def db_fill_country(self, ctx, data, session, user):
        while True:
            rawcountry = await self.db_ask(data, 'country')
            try:
                country = pycountry.countries.lookup(rawcountry)
                user.country = self.db_fetch_or_create(session, country.alpha_3, database.Country, use_code=True)
                session.commit()
                return
            except Exception as e:
                print(e)
                await ctx.bot.whisper('Country not found. Please enter the english name of the country or its alpha-3 code.')

    async def db_fill_tz(self, ctx, data, session, user):
        while True:
            rawtz = await self.db_ask(data, 'timezone')
            try:
                time = utils.display_time_tz(rawtz)
                while True:
                    correct = await self.db_ask_q(data, f'Is this your current time: {time}? (yes/no)')
                    if correct.lower() == 'yes':
                        user.timezone = rawtz
                        session.commit()
                        return
                    elif correct.lower() == 'no':
                        break
            except pytz.UnknownTimeZoneError:
                await ctx.bot.whisper('This is not a valid timezone, please try again.')

    async def db_fill_languages(self, ctx, data, session, user):
        while True:
            rawlang = await self.db_ask(data, 'languages')
            langs = rawlang.split(',')
            languages_data = []
            for lang in langs:
                m = re.match(r'((?:\w+ *)+) *(?:\(([^)]+)\))*', lang.strip())
                if m:
                    try:
                        language = pycountry.languages.lookup(m.group(1).strip())
                        if m.group(2) or language.alpha_3 != 'mis':
                            extra = m.group(2).strip() if m.group(2) else None
                            languages_data.append((language.alpha_3, language.name, extra))
                    except Exception as e:
                        print(e)

            while True:
                datalist = ', '.join(map(lambda x: utils.language_display_string(x[0], x[2], name=x[1]), languages_data))
                correct = await self.db_ask_q(data, f'Is this correct: {datalist}? (yes/no)')
                if correct.lower() == 'yes':
                    previous_lang = session.query(database.Language).filter(database.Language.user_id == user.id).all()
                    if previous_lang:
                        for i in previous_lang:
                            session.delete(i)
                        session.commit()
                    for lang in languages_data:
                        item = database.Language(user_id=user.id, code=lang[0], extra=lang[2])
                        session.add(item)
                    session.commit()
                    return
                elif correct.lower() == 'no':
                    break

    async def db_fill_prog_languages(self, ctx, data, session, user):
        rawlang = await self.db_ask(data, 'prog_languages')
        langs = rawlang.split(',')
        languages_data = []
        for lang in langs:
            m = re.match(r'((?:[^ ()]+ *)+) *(?:\(([^)]+)\))*', lang.strip())
            if m:
                language = m.group(1).strip()
                extra = m.group(2).strip() if m.group(2) else None
                languages_data.append(database.ProgrammingLanguage(user_id=user.id, name=language, extra=extra))

        previous_lang = session.query(database.ProgrammingLanguage).filter(database.ProgrammingLanguage.user_id == user.id).all()
        if previous_lang:
            for i in previous_lang:
                session.delete(i)
            session.commit()
        for lang in languages_data:
            session.add(lang)
        session.commit()


    def db_fetch_or_create(self, session, content, class_name, use_code=False):
        if content is not None:
            if use_code:
                item = session.query(class_name).filter(class_name.code.ilike(content)).first()
            else:
                item = session.query(class_name).filter(class_name.name.ilike(content)).first()
            if item is None:
                if use_code:
                    item = class_name(code=content)
                else:
                    item = class_name(name=content)
                session.add(item)
            return item
        return None

    async def db_ask_date(self, data, question_id):
        while True:
            try:
                content = await self.db_ask(data, question_id)
                if content == None:
                    return None
                datetime.datetime.strptime(content, '%Y-%m-%d').date()
                return content
            except:
                await data['ctx'].bot.whisper('You need to enter a valid date')

    async def db_ask(self, data, question_id):
        await data['ctx'].bot.whisper(self.questions[question_id])
        return await self.db_wait_message(data, default_value=self.default_values.get(question_id))

    async def db_ask_q(self, data, question):
        await data['ctx'].bot.whisper(question)
        return await self.db_wait_message(data)

    async def db_wait_message(self, data, default_value=None):
        message = await data['ctx'].bot.wait_for_message(author=data['user'], channel=data['channel'], timeout=self.timeout)
        if message is None:
            username = data['user'].name
            await data['ctx'].bot.whisper(f'_Dear diary, today I\'ve been completely ignored by {username}. I\'ve never felt so good!_\n[This means the command has timed out, you need to start it again to continue]')
            raise asyncio.TimeoutError

        if message.content.startswith('!'):
            return await self.db_wait_message(data, default_value=default_value)

        if message.content == '-' and default_value:
            return default_value
        return message.content

def setup(bot):
    bot.add_cog(Userdb(bot))
