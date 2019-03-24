#!/usr/bin/env python3

import asyncio
import discord
import inspect
import glob
import random
from discord.ext import commands

from commands import userdb
from utils import database, shared, checks, utils

class Help:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, aliases=['andré', 'Andre', 'André', 'help', 'Help'])
    async def andre(self, ctx, *, command: str = None):

        all_commands = {
            '#Profile': {
                'user setup': {
                    'args': '',
                    'usage': 'Starts the q/a to fill your profile.'
                },
                'user update': {
                    'args': '',
                    'usage': 'Lets you update part of your profile.'
                },
                'user extras setup': {
                    'args': '',
                    'usage': 'Starts the q/a to fill your extras profile.'
                },
                'user extras update': {
                    'args': '',
                    'usage': 'Lets you update part of your extras profile.'
                },
            },

            'User stats': {
                'users': {
                    'args': '[extras]',
                    'usage': 'Prints the list of users who have filled their profile. If extras is specified, also prints tho who have filled their extras profile.'
                },
                'profile': {
                    'args': '[[+]extras] [user]',
                    'usage': 'Shows a user\'s profile (or yours if *user* is unspecified). If extras is specified, print the extras profile questions instead. If +extras is specified, print both'
                },
                'tz': {
                    'args': '[user]',
                    'usage': 'Prints the timezone of the specified user (if no *user* is specified, prints all known users grouped by local time).'
                },
                'stats': {
                    'args': '[field]',
                    'usage': 'Prints a list of members grouped by the specified field. If no *field* is specified, prints the available fields.'
                },
                'projects': {
                    'args': '[name]',
                    'usage': 'Prints details about the specified project. If no *name* is specified, lists all projects.'
                },
                'badges': {
                    'args': '[user]',
                    'usage': 'Shows a user\'s badges (or yours if *user* is unspecified).'
                },
            },

            '#MAL': {
                'search': {
                    'args': '[anime|manga] [search]',
                    'usage': 'Searches for an anime/manga (if unspecified, anime is the default) and prints a short list of the 10 first results.'
                },
                'anime': {
                    'args': '[search|ID]',
                    'usage': 'Searches for an anime and prints basic info about it, plus a list of all members\'s who have the anime in their lists.'
                },
                'manga': {
                    'args': '[search|ID]',
                    'usage': 'Searches for a manga and prints basic info about it, plus a list of all members\'s who have the manga in their lists.'
                },
                'airing': {
                    'args': '[watching] [anime|member]',
                    'usage':
                        """Prints the airing shows in the memebers' lists.
                        If *watching* is specified, only watching anime are considered.
                        If a *anime* filter argument is provided, only print the anime matching the filter.
                        If a *member* filter is provided instead, print the anime in that member's list."""
                },
                'animelist': {
                    'args': '[status] [user]',
                    'usage': 'Prints the user\'s list in the specified status (or you if *user* is unspecified).'
                },
                'mangalist': {
                    'args': '[status] [user]',
                    'usage': 'Prints the user\'s list in the specified status (or you if *user* is unspecified).'
                },
                'nextmal': {
                    'args': '[user]',
                    'usage': 'Prints a random entry from the user\'s PTW list (or you if *user* is unspecified).'
                },
                'shared': {
                    'args': '[anime|manga] [arguments]',
                    'usage':
                        """Prints stats about common anime or manga.
                        *arguments* can be any arrangement of the following, in the format *key=value*:
                        
                        **style**: How to display results. Values: *short*, *details*, *full*. Defaults to details.
                        **results**: Limit how many results to display. 0 means no limit. Defaults to 5.
                        **reverse**: Reverse the sort. Can be true of false. Defaults to false.
                        **sort**: Type of sort to apply. Values: *members* (number of members who shared this anime/manga), *completed* (same but only completed), *score* (average member score). Defaults to members.
                        **min_members**: Can be used with sort=score to only show anime/manga scored by at least that amount of members. Defaults to 0.
                
                        Example: `!shared anime sort=score min_members=10 results=10`"""
                },
                'sao': {
                    'args': '[user]',
                    'usage': 'Prints the SAO scores for the given user (or you if *user* is unspecified).'
                },
                'compare': {
                    'args': '[user1] [user2] [arguments]',
                    'usage':
                        """Compares the lists of the two specified users.
                        *arguments* can be any arrangement of the following, in the format *key=value*:
                        
                        **entity**: *anime* or *manga*. Defaults to anime.
                        **results**: Limit how many results to display. 0 means no limit. Defaults to 20.
                        **min_score**: The minimum score the user must have given for the entity to be included. Defaults to 1.
                        **max_score**: The maximum score the user must have given for the entity to be included. Defaults to 10.
                        **diff_score**: The difference in score between the two users. -1 means no limit. Defaults to -1.
                        **sort**: Type of sort to apply. Values: *similar* (lower difference first) or *different* (higher difference first). Defaults to similar.
                        **group**: Whether to group the results by score difference. Defaults to true.
                
                        Example: `!compare usera userb group=false results=10 diff_score=3`"""
                },
                'affinity': {
                    'args': '[user1] [user2] [anime|manga]',
                    'usage': 'Prints the affinity scores between the two users. If user1 is not specified, use your username instad. If user2 is not specified, compare with all other members.'
                },
                'unique': {
                    'args': '[anime|manga] [user_comparing] user_to_compare',
                    'usage': 'Finds unique anime/manga from *user_comparing*\'s list that *user_to_compare* has not watched/read yet, and sort them by score. *user_comparing* will be set to you if not specified.'
                },
                'when': {
                    'args': '[anime|manga] [title]',
                    'usage': 'Prints the start/end dates of an anime/manga (if unspecified, anime is the default).'
                },
                'scoredistribution': {
                    'args': '[arguments]',
                    'usage':
                        """Prints the score distribution of users in the server.
                        *arguments* can be any arrangement of the following, in the format *key=value*:

                        **entity**: *anime* or *manga*. Defaults to anime.
                        **score**: Show the distribution for a specific score [1-10]. Defaults to None.
                        **sort**: Type of sort to apply. Values: 
                            *percent* (sort by percent of the specific score in the list)
                            *amount* (sort by most of a specific score in the list)
                            *balanced* (sort by percent * amount)
                        Defaults to percent.

                        Example: `!scoredistribution entity=manga score=8`"""
                },
                'meanscores': {
                    'args': '[anime|manga]',
                    'usage': 'Prints the mean score of all the users.'
                }
            },

            'VNDB': {
                'vndb': {
                    'args': '',
                    'usage': 'Prints detailed help about the vndb commands.'
                },
                'vndbalias': {
                    'args': '',
                    'usage': 'Prints usage for adding or removing vndb aliases.'
                },
                'vn': {
                    'args': '[options] [id|name]',
                    'usage': 'Displays the specified VN. See `!vndb` for more details on the available options.'
                },
                'vns': {
                    'args': '[name]',
                    'usage': 'Searches for VNs with the specified name.'
                },
                'vnt': {
                    'args': '[options] [id|name]',
                    'usage': 'Displays the tags of the specified VN. See `!vndb` for more details on the available options.'
                },
                'vnc': {
                    'args': '[options] [id|name]',
                    'usage': 'Displays the specified VN character. See `!vndb` for more details on the available options.'
                },
                'vncs': {
                    'args': '[name]',
                    'usage': 'Searches for VN characters with the specified name.'
                },
                'vnct': {
                    'args': '[options] [id|name]',
                    'usage': 'Displays the traits of the specified VN character. See `!vndb` for more details on the available options.'
                },
                'vndbapi': {
                    'args': '[id]',
                    'usage': 'Returns a json string containing the requested character. The json output is always wrapped around triple backquotes.'
                },
            },

            'User lists': {
                'mal': {
                    'args': '[user]',
                    'usage': 'Prints basic MAL info for the specified user (or you if *user* is unspecified).'
                },
                'scores': {
                    'args': '[anime|manga] [user] [filter]',
                    'usage':
                        """Prints the score distribution for the specified user (or you if *user* is unspecified).
                        If *anime* or *manga* is not specified, anime will be used as the default.
                        If a *filter* argument is provided, it will instead print all anime/manga matching the score filter.
                        *filter* can be one of the following: `n`, `=n`, `<n`, `<=n`, `>n` or `>=n` where n is in [0, 10]
                        
                        Scores are considered shamful if given to PTW anime or dropped anime (unless you have watched 80% or more than 50 eps)"""
                },
            },

            '#Languages': {
                'moonrunes': {
                    'args': '[runes]',
                    'usage': 'Translates the given Japanese text. If no argument is provided, translate the last 10 messages'
                },
                'tr': {
                    'args': '[[from]=>to] text',
                    'usage': 'Translates the given text. If no language is specified, it will translate to english.'
                },
            },

            'Random': {
                'about': {
                    'args': '',
                    'usage': 'Prints info about André'
                },
                'updatelist': {
                    'args': '[user]',
                    'usage': 'Updates your (or *user*\'s) lists cache.'
                },
                'bots': {
                    'args': '',
                    'usage': 'Prints a short description of this server\'s bots.'
                },
                'school': {
                    'args': '[year]',
                    'usage': 'Translates a school year (grade). If *year* is not specified, prints the entire conversion table.'
                },
                'ping': {
                    'args': '',
                    'usage': 'It\'s a ping command. It pings the bot. What pings commands are supposed to do.'
                },
                'quote': {
                    'args': '',
                    'usage': 'Get a random inspirational quote.'
                },
                'exec': {
                    'args': '[command] [;; command]*',
                    'usage': 'Evaluates the commands separated by ;; in order.'
                },
                'bc': {
                    'args': '[expr]',
                    'usage': 'Evaluates the expression using the ExprTk math library. You may wrap your expression around backquotes.'
                },
            },

            'Special': {
                'eva': {
                    'args': '',
                    'usage': 'It does nothing.'
                },
                'noop': {
                    'args': '',
                    'usage': 'It does nothing.'
                },
                'meesterp': {
                    'args': '',
                    'usage': 'An alias for `!exec !updatelist ;; !airing @me`.'
                },
            },

            'Database': {
                'db users': {
                    'args': '[fmt]',
                    'usage': 'Dumps the saved users\' discord_id/mal_name. Default fmt is `{0}:{1}`'
                },
            },

            ##### Admin

            '!Admin': {
                'whois': {
                    'args': '[user]',
                    'usage': 'Displays the different names for the specified user.'
                },
                'newgame': {
                    'args': '[game]',
                    'usage': 'Updates André\'s current game. If *game* in unspecified, takes a random game. Enables the random game rotation'
                },
                'setgame': {
                    'args': '[type] [game]',
                    'usage': 'Updates André\'s current game. Disables the random game rotation.'
                },
                'clearcache': {
                    'args': '',
                    'usage': 'Clears all lists cache.'
                },
                'admin': {
                    'args': '',
                    'usage': 'Starts André\'s interactive mode.'
                },
                'moonrunes auto': {
                    'args': '[enable/disable]',
                    'usage': 'Enables/Disables automatic moonrune translation for the current channel.'
                },
                'update': {
                    'args': '[force]',
                    'usage': 'Runs `git pull` and restarts the bot.'
                },
                'restart': {
                    'args': '[force]',
                    'usage': 'Restarts the bot.'
                },
                'shutdown': {
                    'args': '',
                    'usage': 'This kills the bot.'
                },
                'say': {
                    'args': '[message]',
                    'usage': 'Prints the message.'
                },
                'for': {
                    'args': '[n] [command]',
                    'usage': 'Executes the command *n* times.'
                },
                'avatar': {
                    'args': '',
                    'usage': 'Runs the script that changes my avatar.'
                },
                'birthday': {
                    'args': '',
                    'usage': 'Checks members\' birthdays.'
                },
                'birthdaytime': {
                    'args': '',
                    'usage': 'Prints time remaining before next birthday check.'
                },
                'extrasdb': {
                    'args': '[subcommand]',
                    'usage': 'Manage the extras db. If no subcommand is passed, prints an help message.'
                },
                'backupdb': {
                    'args': '',
                    'usage': 'Makes a backup of the database.'
                },
                'purgedb': {
                    'args': '[mal_name or discord_id] [field_name]',
                    'usage':
                        """Removes the db field for the selected user.
                        Will always make a backup of the database beforehand.
                        If `*` is provided, remove the user completely.
                        Accepted fields are: 'mal_name', 'gender', 'birthdate', 'bio', 'timezone', 'languages', 'prog_languages', 'projects', 'extras'"""
                },
                'ignorenickname': {
                    'args': '[user] [true|false]',
                    'usage': 'If true, the nickname of this user will not be considered when displaying names.'
                },
                'botstate': {
                    'args': '',
                    'usage': 'Prints the running user commands.'
                },
                'clearbotstate': {
                    'args': '',
                    'usage': 'Clears the running user commands state.'
                },
                'badgesdb': {
                    'args': '[subcommand]',
                    'usage': 'Manage the badges db. If no subcommand is passed, prints an help message.'
                },
                'setmalembed': {
                    'args': 'link_template',
                    'usage': 'Sets the MALembed link template. use `<username>` as a placeholder for the username.'
                },
                'ban': {
                    'args': '[member]',
                    'usage': 'Bans the member from using commands'
                },
                'bans': {
                    'args': '',
                    'usage': 'List the current bans'
                },
                'unban': {
                    'args': '[member]',
                    'usage': 'Unban the member'
                },
            }
        }

        message = ''
        if command:
            command = command.lower()
            for category, command_lists in all_commands.items():
                for name, info in command_lists.items():
                    if command == name:
                        if category.startswith('!') and not checks.is_owner_check(ctx.message):
                            await ctx.bot.say('This is top secret, sorry.')
                        else:
                            args = f' {info["args"]}' if info["args"] else ''
                            usage = inspect.cleandoc(info['usage'])
                            await ctx.bot.say(f'`!{command}{args}`\n\n{usage}')
                        return
            message += f'Unknown command `{command}`\n\n'

        message += '```Available commands```'
        for category, items in all_commands.items():
            if category.startswith('!') and not checks.is_owner_check(ctx.message):
                pass
            else:
                if category.startswith('#') or category.startswith('!'):
                    message += f'\n**{category[1:]}** - '
                else:
                    message += f'**{category}** - '
                message += ', '.join(map(lambda name: f'*{name}*', items.keys()))
                message += '\n'

        message += '\n\nType `!help [command]` to get more info for a specific command.'
        await utils.safe_say(ctx, message)


    @commands.command(pass_context=True, aliases=['About'])
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def about(self, ctx, extra=None):
        if extra == '--monika':
            message = await ctx.bot.say(embed=self.get_about_message(ctx, monika=True))
            await asyncio.sleep(random.randint(3, 5))
            await ctx.bot.edit_message(message, embed=self.get_about_message(ctx))
        else:
            await ctx.bot.say(embed=self.get_about_message(ctx))

    def get_about_message(self, ctx, monika=False):
        message = discord.Embed()

        if monika:
            message.set_author(name=f'Monika', icon_url='http://cecc.at/discord/monika.png')
            message.set_thumbnail(url='http://cecc.at/discord/monika.png')
            message.colour = 0xFFB6C1
            description = 'Hello, I\'m just Monika.\n\n'
        else:
            message.set_author(name=f'André', icon_url='http://cecc.at/discord/andre.png')
            message.set_thumbnail(url='http://cecc.at/discord/andre-thumb.png')
            message.colour = 0xF1CCB0
            description = 'Hello, I am アンドレ, a discord bot made by IATGOF.\n\n'

        description += f'**Version**: {shared.version}\n'

        stats = self.get_source_stats()
        description += f'**Stats**: {stats[1]} lines of python across {stats[0]} files.\n\n'

        if monika:
            description += f"""Latest changes:
```An exception has occured.
See traceback.txt for details.```"""
        else:
            description += f"""`This bot is discountinued`"""

        message.description = description
        return message

    def get_source_stats(self):
        files = glob.glob('./**/*.py', recursive=True)
        files = [f for f in files if 'db_migrate' not in f and 'dbmanage' not in f and 'kanji_to_romaji' not in f]

        nlines = 0
        for file in files:
            with open(file, encoding="utf8") as f:
                nlines += sum(1 for line in f if line.rstrip())
        return len(files), nlines

    @commands.command(pass_context=True)
    async def bots(self, ctx):
        bots = [
            {
                'name': 'André',
                'user': 'IATGOF',
                'user_id': '9154',
                'description': 'Its purpose is mainly to store profiles for members of this discord and offer some stats and utility around those profiles.',
                'prefix': '!',
                'about': 'about',
                'help': 'help'
            },
            {
                'name': 'Kaneda',
                'user': 'Benpai',
                'user_id': '9772',
                'description': 'It offers a lot of general utility commands.',
                'prefix': 'k/',
                'about': 'about',
                'help': 'help'
            },
            {
                'name': 'Neko-Hime',
                'user': 'Xaetral - アロヒス',
                'user_id': '3486',
                'description': 'Its main uses are to provide custom reaction image and youtube search, but it also has some more utility commands.',
                'prefix': 'n:',
                'about': 'infos',
                'help': 'help'
            },
            {
                'name': 'Sakanya',
                'user': 'FoxInFlame',
                'user_id': '9833',
                'description': 'Its primary goal is to reverse-search images, however it also offers utility commands, some of which help Fox manage this server efficiently.',
                'prefix': '>',
                'about': 'about',
                'help': 'help'
            },
            {
                'name': 'Margarine',
                'user': 'Butterstroke',
                'user_id': '7150',
                'description': 'It\'s a lovely and helpful bot (he can\'t math though).',
                'prefix': 'm~',
                'about': 'about',
                'help': 'help'
            },
            {
                'name': 'BobDono',
                'user': 'Drutol',
                'user_id': '5419',
                'description': 'Bob is waifu connoisseur. He is here for your all waifu needs. If you ever need to make others wail in despair because of your waifu\'s superiority he can make waifu wars just for you!',
                'prefix': 'b/',
                'about': 'bob',
                'help': 'bob'
            }
        ]

        message = ''
        for item in bots:
            message += f"""**{item['name']}** is a bot made by **{item['user']}**#{item['user_id']}.
{item['description']}
For more details, type `{item['prefix']}{item['about']}`
For a list of **{item['name']}**'s commands, type `{item['prefix']}{item['help']}`

"""

        await ctx.bot.say(message)


def setup(bot):
    bot.add_cog(Help(bot))
