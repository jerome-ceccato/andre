#!/usr/bin/env python3

import asyncio
import discord
import datetime
import pytz
import pycountry
from babel.dates import format_timedelta
from discord.ext import commands

from commands import userdb, mal
from utils import database, shared, utils, checks

class UserAction:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, aliases=['Profile'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def profile(self, ctx, first_param: str = None, second_param: str = None):

        show_extra = None
        if first_param and (first_param in ['extra', 'extras', '+extra', '+extras']):
            member_raw = second_param
            show_extra = first_param
        elif second_param and (second_param in ['extra', 'extras', '+extra', '+extras']):
            member_raw = first_param
            show_extra = second_param
        else:
            member_raw = first_param

        member = await utils.convert_member(ctx, member_raw, optional=True)
        if member is None:
            member = ctx.message.author

        session = database.new_session()
        user = session.query(database.User).filter(database.User.discord_id == member.id).first()

        if user is None:
            await ctx.bot.say(f'No data recorded for {member.name}')
            return

        if not show_extra or show_extra.startswith('+'):
            await ctx.bot.say(embed=self.profile_main_message(ctx, user, member, session, show_extra))
        if show_extra:
            message = self.profile_extra_message(ctx, session, user, member)
            if message:
                await utils.force_say(message, ctx.bot.say)

    def profile_main_message(self, ctx, user, member, session, show_extra):
        true_name = utils.UserLookup.display_name_with_context(ctx, member)
        title = f'{true_name} - {user.mal_name}' if true_name and true_name.lower() != user.mal_name.lower() else user.mal_name

        url = f'https://myanimelist.net/profile/{user.mal_name}' if user.mal_name else None
        message = discord.Embed(title=title, url=url)

        if user.mal_name:
            picture = utils.silent_picture_grab(user.mal_name)
            if picture:
                message.set_thumbnail(url=picture)

        content = '\n'
        if user.gender is not None:
            content += f'**Gender**: {user.gender}\n'
        if user.birthdate is not None and utils.is_birthdate_valid(user.birthdate):
            age = utils.age_from_birthdate(user.birthdate)
            content += f'**Age**: {age}\n'
        if user.country is not None:
            country = pycountry.countries.get(alpha_3=user.country.code.upper())
            content += f'**Country**: {country.name}\n'
        if user.timezone is not None:
            content += f'**Local time**: {utils.display_time_tz(user.timezone)} ({user.timezone})\n'
        if user.languages:
            value = ', '.join(map(lambda x: utils.language_display_string(x.code, x.extra), user.languages))
            content += f'**Spoken languages**: {value}\n'
        if user.prog_languages:
            value = ', '.join(map(lambda x: utils.prog_language_display_string(x.name, x.extra), user.prog_languages))
            content += f'**Programming languages**: {value}\n'
        if user.bio is not None:
             content += f'**About {true_name}**: {user.bio}\n'

        content += '\n'
        if user.projects:
            content += 'Project(s):\n' + '\n\n'.join(map(utils.project_content, user.projects))
        else:
            content += f'There are no projects listed for {true_name}.'

        showing_extra_infos = False
        if not show_extra:
            user_extras = session.query(database.UserExtras).filter(database.UserExtras.user_id == user.id).first()
            if user_extras:
                if not showing_extra_infos:
                    content += '\n'
                    showing_extra_infos = True
                content += f'\n{true_name} has extra infos available. Run **!profile {true_name} extras** to see them.'

        user_badges = session.query(database.UserBadge).filter(database.UserBadge.user_id == user.id).count()
        if user_badges:
            plural = 's' if user_badges > 1 else ''
            plural2 = 'them' if user_badges > 1 else 'it'
            if not showing_extra_infos:
                content += '\n'
                showing_extra_infos = True
            content += f'\n{true_name} has collected {user_badges} badge{plural}. Run **!badges {true_name}** to see {plural2}.'

        message.description = content
        return message

    def profile_extra_message(self, ctx, session, user, member):
        true_name = utils.UserLookup.display_name_with_context(ctx, member)
        message = f'*{true_name}\'s extra profile*\n\n'

        extras = session.query(database.Extras).all()
        user_extras = session.query(database.UserExtras).filter(database.UserExtras.user_id == user.id).all()

        if not extras or not user_extras:
            return None

        lookup = {}
        for item in extras:
            lookup[item.id] = item

        for user_extra in user_extras:
            message += f'**{lookup[user_extra.extras_id].question}** {user_extra.response}\n'

        return message

    @commands.command(pass_context=True, aliases=['Tz', 'timezone'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def tz(self, ctx, member_raw: str = None):
        member = await utils.convert_member(ctx, member_raw, optional=True)
        if member is None:
            user_lookup = utils.UserLookup(ctx.bot)
            session = database.new_session()
            users = session.query(database.User).filter(database.User.timezone.isnot(None)).all()

            timezones = {}
            now = datetime.datetime.utcnow()
            for user in users:
                local_time = pytz.utc.localize(now, is_dst=None).astimezone(pytz.timezone(user.timezone))
                key = local_time.strftime('%Y%m%d %H:%M:%S')
                if key in timezones:
                    timezones[key]['data'].append(user)
                else:
                    timezones[key] = {'tz': local_time, 'data': [user]}

            days_tz = {}
            for key in timezones.keys():
                day_string = key.split(' ')[0]
                if day_string not in days_tz:
                    days_tz[day_string] = []
                days_tz[day_string].append({'sorting': key, 'time': timezones[key]['tz'], 'users': timezones[key]['data']})

            sorted_tz = {k: sorted(v, key=lambda x: x['sorting']) for k, v in days_tz.items()}

            flat_tz = []
            for item in sorted_tz.keys():
                flat_tz.append({'day': item, 'data': sorted_tz[item]})

            final_tz = sorted(flat_tz, key=lambda x: x['day'])

            message = ''
            for day in final_tz:
                day_string = day['data'][0]['time'].strftime('%A')
                message += f'**{day_string}:**\n\n'
                for item in day['data']:
                    display_time = item['time'].strftime('%H:%M:%S')
                    tz_users = ', '.join(map(lambda x: f'{user_lookup.display_name_from_mal(x.mal_name)} *({x.timezone})*', item['users']))
                    message += f'{display_time}:\n{tz_users}\n\n'
            await utils.safe_say(ctx, message)

        else:
            session = database.new_session()
            user = session.query(database.User).filter(database.User.discord_id == member.id).first()

            if user is None or user.timezone is None:
                await ctx.bot.say(f'{utils.UserLookup.display_name_from_user(member)} has not set their timezone!')
                return

            tz = pytz.timezone(user.timezone)
            time = pytz.utc.localize(datetime.datetime.utcnow(), is_dst=None).astimezone(tz)
            timezone_string = time.strftime('%A %H:%M:%S')
            await ctx.bot.say(f'{timezone_string} ({user.timezone})\n')

    @commands.command(pass_context=True, aliases=['Users'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def users(self, ctx, extras: str = None):
        session = database.new_session()
        users = session.query(database.User).all()

        lookup = {}
        for user in users:
            lookup[user.discord_id] = user

        registered_users_raw = []
        registered_users = []
        new_users = []
        mal_users = lookup

        server_id = ctx.message.server.id if ctx.message.server and ctx.message.server.id else shared.main_server_id
        server = ctx.bot.get_server(server_id)
        for member in server.members:
            if not member.bot:
                true_name = utils.UserLookup.display_name_from_user(member)
                if member.id in lookup:
                    if true_name == lookup[member.id].mal_name:
                        registered_users.append(true_name)
                    else:
                        registered_users.append(f'{true_name} *({lookup[member.id].mal_name})*')
                    registered_users_raw.append(member)
                    mal_users.pop(member.id)
                else:
                    new_users.append(true_name)

        message = ''
        if registered_users:
            message += '**Registered users**:\n'
            message += ', '.join(registered_users)
            message += '\n\n'
        if new_users:
            message += '**Users who have not filled their profile yet** (type `!user setup`):\n'
            message += ', '.join(new_users)
            message += '\n\n'
        if mal_users:
            message += '**Registered users who are not in this server**:\n'
            message += ', '.join(map(lambda x: x.mal_name, mal_users.values()))
            message += '\n\n'

        if extras and extras in ['extra', 'extras']:
            message += 'Registered users with an extras profile:\n'

            user_extras = session.query(database.UserExtras).all()
            extras_lookup = {}
            for item in user_extras:
                extras_lookup[item.user_id] = item

            user_extra_profile = []
            for user in registered_users_raw:
                if lookup[user.id].id in extras_lookup:
                    user_extra_profile.append(utils.UserLookup.display_name_from_user(user))

            message += ', '.join(user_extra_profile)
            message += '\n\n'


        await utils.safe_say(ctx, message)

    @commands.command(pass_context=True, aliases=['Projects', 'Project', 'project'], rest_is_raw=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def projects(self, ctx, *, project_name: str = None):
        user_lookup = utils.UserLookup(ctx.bot)

        if not project_name:
            session = database.new_session()
            projects = sorted(session.query(database.Project).all(), key=lambda proj: proj.name)
            users = session.query(database.User).all()

            lookup = {}
            for user in users:
                for p in user.projects:
                    if p.id not in lookup:
                        lookup[p.id] = []
                    if user.mal_name:
                        lookup[p.id].append(user_lookup.display_name_from_mal(user.mal_name))

            message = '\n'.join(map(lambda x: self.project_string(x, lookup), projects))
            await utils.safe_say(ctx, f'Use `!project [project_name]` to get details about a project.\n\n{message}')
        else:
            project_name = project_name.strip()
            session = database.new_session()
            await ctx.bot.say(self.project_build_message(ctx, session, user_lookup, project_name))

    def project_string(self, project, users_lookup):
        if project.id in users_lookup:
            usernames = ', '.join(users_lookup[project.id])
            return f'{project.name} *({usernames})*'
        return project.name

    def project_build_message(self, ctx, session, user_lookup, project_name):
        fuzzy_name = f'%{project_name}%'
        projects = session.query(database.Project).filter(database.Project.name.ilike(fuzzy_name)).all()
        if not projects:
            return f'No project found with the name `{project_name}`'

        message = ''
        if len(projects) > 1:
            names = ', '.join(map(lambda x: x.name, projects))
            message += f'Multiple projects found for *{project_name}*: {names}\nPrinting first match only:\n\n'

        project = projects[0]
        users = session.query(database.User).join(database.User.projects).filter(database.User.projects.contains(project)).all()
        flat_users = ', '.join(map(lambda x: user_lookup.display_name_from_mal(x.mal_name), users))
        message += f'**{project.name}** by {flat_users}'
        if project.description is not None:
            message += f'\n{project.description}'
        if project.link is not None:
            message += f'\n{project.link}'
        return message

    @commands.command(pass_context=True, aliases=['score', 'Scores', 'Score'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def scores(self, ctx, entity: str = 'anime', member_raw: str = None, score: str = None):
        entity = entity.lower()
        if entity not in ['anime', 'manga']:
            score = member_raw
            member_raw = entity
            entity = 'anime'

        member = await utils.convert_member(ctx, member_raw, optional=True, print_error=False, critical_failure=False)
        mal_name = await utils.require_mal_username(ctx, member)
        if not mal_name:
            return

        if member_raw and not member and not score:
            score = member_raw

        await shared.cache.require_entity_list(ctx, mal_name, entity)
        data = mal.make_maluser(mal_name, entity)

        if score is None:
            message = f'{utils.UserLookup.display_name_with_context(ctx, member)}\'s list:\n\n'
            for i in range(10, -1, -1):
                percent = len(data.scores[i]) * 100.0 / data.total_scored if data.total_scored > 0 else 0
                nb_completed = 0
                for item in data.scores[i]:
                    status = item.get('watched_status', item.get('read_status', ''))
                    if i == 0:
                        if status == 'completed':
                            nb_completed += 1
                    else:
                        if status in ['completed', 'watching', 'reading', 'on-hold']:
                            nb_completed += 1
                        elif status in ['dropped']:
                            if entity == 'anime':
                                nb_eps = item.get('episodes', 0)
                                w_eps = item.get('watched_episodes', 0)
                                if (nb_eps and (w_eps / nb_eps >= 0.8)) or (w_eps > 50):
                                    nb_completed += 1

                if i == 0:
                    message += f'**No score**: {nb_completed}'
                    if nb_completed == 0:
                        message += f' \\{shared.reaction_ok}\n'
                    else:
                        message += f' \\{shared.reaction_ko}\n'
                else:
                    percent_string = '({0:.1f}%)'.format(percent)
                    message += f'**{i}**: {len(data.scores[i])} {percent_string}'
                    if nb_completed != len(data.scores[i]):
                        total = len(data.scores[i]) - nb_completed
                        message += f' \\{shared.reaction_ko} ({total})\n'
                    else:
                        message += f' \\{shared.reaction_ok}\n'

            await ctx.bot.say(message)
        else:
            def get_value(score, split):
                try:
                    value = int(score[split:])
                except:
                    value = 10
                return value

            if score.startswith('>='):
                scores = range(10, get_value(score, 2) - 1, -1)
            elif score.startswith('>'):
                scores = range(10, get_value(score, 1), -1)
            elif score.startswith('<='):
                scores = range(1, get_value(score, 2) + 1)
            elif score.startswith('<'):
                scores = range(1, get_value(score, 1))
            elif score.startswith('='):
                scores = [get_value(score, 1)]
            else:
                scores = [get_value(score, 0)]

            max_size = 2000 - len('\n[...]')
            message = f'{utils.UserLookup.display_name_with_context(ctx, member)}\'s list:\n'
            for i in scores:
                if len(data.scores[i]) > 0:
                    part = f'\n**{i}**:\n'
                    if len(message) + len(part) > max_size:
                        message += '[...]'
                        await ctx.bot.say(message)
                        return
                    else:
                        message += part

                    for item in data.scores[i]:
                        status = item.get('watched_status', item.get('read_status', ''))
                        if status == 'completed':
                            part = f'{item["title"]}\n'
                        else:
                            part = f'{item["title"]} ({status})\n'

                        if len(message) + len(part) > max_size:
                            message += '[...]'
                            await ctx.bot.say(message)
                            return
                        else:
                            message += part

            if len(message) == 0:
                message = 'No match for your filter.'
            await ctx.bot.say(message)


    @commands.command(pass_context=True, aliases=['Stats', 'Stat', 'stat'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def stats(self, ctx, subcommand: str = None, arg: str = None):
        if not subcommand:
            await ctx.bot.say('Available stats: `age`, `gender`, `country`, `language`, `prog`, `anime`, `manga`')
            return

        user_lookup = utils.UserLookup(ctx.bot)

        subcommand = subcommand.lower()
        if subcommand in ['age', 'ages']:
            await utils.safe_say(ctx, self.stat_age(ctx, user_lookup))
        elif subcommand in ['gender', 'genders']:
            await utils.safe_say(ctx, self.stat_gender(ctx, user_lookup, arg))
        elif subcommand in ['country', 'countries']:
            await utils.safe_say(ctx, self.stat_country(ctx, user_lookup, arg))
        elif subcommand in ['language', 'languages']:
            await utils.safe_say(ctx, self.stat_language(ctx, user_lookup, arg))
        elif subcommand in ['prog', 'programming', 'prog_language', 'prog_languages']:
            await utils.safe_say(ctx, self.stat_prog(ctx, user_lookup, arg))
        elif subcommand in ['a', 'anime', 'animelist']:
            await self.entity_stats(ctx, user_lookup, arg, entity='anime')
        elif subcommand in ['m', 'manga', 'mangalist']:
            await self.entity_stats(ctx, user_lookup, arg, entity='manga')

    def stat_age(self, ctx, user_lookup):
        def true_age(birthdate):
            return str(utils.age_from_birthdate(birthdate)) if utils.is_birthdate_valid(birthdate) else 'Unknown'

        return self.util_list_all(wants_stat_grouping=True,
                                  wants_grouping_detail=True,
                                  valid_user_check=lambda user: user.birthdate,
                                  get_grouping_properties=lambda user: [(None, true_age(user.birthdate))],
                                  get_display_string=lambda user, property: user_lookup.display_name_from_mal(user.mal_name),
                                  sorting=None,
                                  formatted_group_name=lambda item, _: item)

    def stat_country(self, ctx, user_lookup, arg):
        grouping = arg and arg.lower() in ['count', 'total']
        return self.util_list_all(wants_stat_grouping=grouping,
                                  wants_grouping_detail=False,
                                  valid_user_check=lambda user: user.country,
                                  get_grouping_properties=lambda user: [(None, pycountry.countries.get(alpha_3=user.country.code.upper()).name)],
                                  get_display_string=lambda user, property: user_lookup.display_name_from_mal(user.mal_name),
                                  sorting=stat_sort_count if grouping else None,
                                  formatted_group_name=lambda item, _: item)

    def stat_gender(self, ctx, user_lookup, arg):
        grouping = arg and arg.lower() in ['count', 'total']
        return self.util_list_all(wants_stat_grouping=grouping,
                                  wants_grouping_detail=False,
                                  valid_user_check=lambda _: True,
                                  get_grouping_properties=lambda user: [(None, (user.gender or 'Unknown').lower())],
                                  get_display_string=lambda user, property: user_lookup.display_name_from_mal(user.mal_name),
                                  sorting=stat_sort_count if grouping else None,
                                  formatted_group_name=lambda item, _: item)

    def stat_prog(self, ctx, user_lookup, arg):
        def language_grouping(lang):
            return lang, lang.name.lower()

        def language_display_string(user, lang):
            if lang.extra:
                return f'{user_lookup.display_name_from_mal(user.mal_name)} ({lang.extra})'
            return user_lookup.display_name_from_mal(user.mal_name)

        def language_title(item, content):
            if len(content) > 0:
                return content[0][1].name
            return item

        grouping = arg and arg.lower() in ['count', 'total']
        return self.util_list_all(wants_stat_grouping=grouping,
                                  wants_grouping_detail=False,
                                  valid_user_check=lambda user: user.prog_languages,
                                  get_grouping_properties=lambda user: map(language_grouping, user.prog_languages),
                                  get_display_string=language_display_string,
                                  sorting=stat_sort_count if grouping else None,
                                  formatted_group_name=language_title)

    def stat_language(self, ctx, user_lookup, arg):
        def language_grouping(lang):
            if lang.code == 'mis':
                return lang, lang.extra
            try:
                return lang, pycountry.languages.get(alpha_3=lang.code).name
            except Exception as e:
                print(e)
                return lang, '_'

        def language_display_string(user, lang):
            if lang.code == 'mis':
                return user_lookup.display_name_from_mal(user.mal_name)
            if lang.extra:
                return f'{user_lookup.display_name_from_mal(user.mal_name)} ({lang.extra})'
            return user_lookup.display_name_from_mal(user.mal_name)

        grouping = arg and arg.lower() in ['count', 'total']
        return self.util_list_all(wants_stat_grouping=grouping,
                                  wants_grouping_detail=False,
                                  valid_user_check=lambda user: user.languages,
                                  get_grouping_properties=lambda user: map(language_grouping, user.languages),
                                  get_display_string=language_display_string,
                                  sorting=stat_sort_count if grouping else None,
                                  formatted_group_name=lambda item, _: item)

    def util_list_all(self, wants_stat_grouping, wants_grouping_detail, valid_user_check, get_grouping_properties, get_display_string, sorting, formatted_group_name):
        session = database.new_session()
        users = session.query(database.User).all()

        items_lookup = {}
        for user in users:
            if valid_user_check(user) and user.mal_name:
                properties = get_grouping_properties(user)
                for meta, property in properties:
                    if property in items_lookup:
                        items_lookup[property].append((user, meta))
                    else:
                        items_lookup[property] = [(user, meta)]

        sorted_items = sorting(items_lookup) if sorting else sorted(items_lookup.keys())
        message = ''
        for item in sorted_items:
            if wants_grouping_detail:
                message += f'`{formatted_group_name(item, items_lookup[item])}: `'
            else:
                message += f'**{formatted_group_name(item, items_lookup[item])}**: '
            n = len(items_lookup[item])
            if wants_stat_grouping:
                if wants_grouping_detail:
                    message += f' **{n}**'
                else:
                    message += f' {n}'

            names = ', '.join(map(lambda x: get_display_string(x[0], x[1]), items_lookup[item]))
            if wants_stat_grouping:
                if wants_grouping_detail:
                    message += f' *({names})*'
            else:
                message += f'{names}'

            message += '\n'

        return message

    async def entity_stats(self, ctx, user_lookup, subcommand, entity):
        if not subcommand:
            if entity == 'anime':
                await ctx.bot.say('Available anime stats: `score`, `episodes`, `days`, `watching`, `completed`, `on-hold`, `dropped`, `ptw`, `start`')
            else:
                await ctx.bot.say('Available manga stats: `score`, `volumes`, `chapters`, `days`, `reading`, `completed`, `on-hold`, `dropped`, `ptr`, `start`')
            return

        if entity == 'anime':
            statuses_map = {
                'watching': 'watching',
                'completed': 'completed',
                'on-hold': 'on_hold',
                'onhold': 'on_hold',
                'on hold': 'on_hold',
                'dropped': 'dropped',
                'ptw': 'plan_to_watch',
                'plan to watch': 'plan_to_watch',
                'planned': 'plan_to_watch'
            }
        else:
            statuses_map = {
                'reading': 'reading',
                'completed': 'completed',
                'on-hold': 'on_hold',
                'onhold': 'on_hold',
                'on hold': 'on_hold',
                'dropped': 'dropped',
                'ptr': 'plan_to_read',
                'plan to read': 'plan_to_read',
                'planned': 'plan_to_read'
            }

        subcommand = subcommand.lower()
        lists = await self.grab_proper_lists(ctx, entity)
        if subcommand in ['score', 'scores']:
            await utils.safe_say(ctx, self.stat_entity_score(ctx, user_lookup, lists))
        elif entity == 'anime' and subcommand in ['episodes', 'episode', 'count']:
            await utils.safe_say(ctx, self.stat_entity_metric(ctx, user_lookup, lists, 'total_episodes'))
        elif entity == 'manga' and subcommand in ['chapter', 'chapters']:
            await utils.safe_say(ctx, self.stat_entity_metric(ctx, user_lookup, lists, 'total_chapters'))
        elif entity == 'manga' and subcommand in ['volume', 'volumes']:
            await utils.safe_say(ctx, self.stat_entity_metric(ctx, user_lookup, lists, 'total_volumes'))
        elif subcommand in ['day', 'days', 'time']:
            await utils.safe_say(ctx, self.stat_entity_metric(ctx, user_lookup, lists, 'days'))
        elif subcommand in statuses_map.keys():
            await utils.safe_say(ctx, self.stat_entity_status(ctx, user_lookup, lists, statuses_map[subcommand]))
        elif subcommand in ['start', 'started']:
            await utils.safe_say(ctx, self.stat_entity_start_date(ctx, user_lookup, lists))

    async def grab_proper_lists(self, ctx, entity):
        raw = await shared.cache.require_entity_lists(ctx, entity)
        return map(lambda x: mal.make_maluser(x, entity), raw.keys())

    def stat_entity_score(self, ctx, user_lookup, lists):
        lists = sorted(lists, key=lambda x: x.mean_score, reverse=True)
        message = ''
        for user in lists:
            message += '**{0}**: {1:.2f} ({2} scores)\n'.format(user_lookup.display_name_from_mal(user.mal_name), user.mean_score, user.total_scored)
        return message

    def stat_entity_metric(self, ctx, user_lookup, lists, field):
        lists = sorted(lists, key=lambda x: getattr(x, field), reverse=True)
        message = ''
        for user in lists:
            message += '**{0}**: {1}\n'.format(user_lookup.display_name_from_mal(user.mal_name), getattr(user, field))
        return message

    def stat_entity_status(self, ctx, user_lookup, lists, status):
        lists = sorted(lists, key=lambda x: len(getattr(x, status)), reverse=True)
        message = ''
        for user in lists:
            message += '**{0}**: {1}\n'.format(user_lookup.display_name_from_mal(user.mal_name), len(getattr(user, status)))
        return message

    def stat_entity_start_date(self, ctx, user_lookup, lists):
        lists = sorted(lists, key=lambda x: (x.min_start_date is None, x.min_start_date))
        message = ''
        for user in lists:
            message += '**{0}**: {1}\n'.format(user_lookup.display_name_from_mal(user.mal_name), start_date_display_string(user.min_start_date))
        return message

def start_date_display_string(date):
    if date:
        current = datetime.datetime.strptime(date, '%Y-%m-%d')
        difference = format_timedelta(current - datetime.datetime.now(), granularity='days', locale='en_US')
        return f'{difference} ago *({date})*'
    return '*Unknown*'

def stat_sort_count(lookup):
    return sorted(lookup.keys(), key=lambda x: len(lookup[x]), reverse=True)

def setup(bot):
    bot.add_cog(UserAction(bot))
