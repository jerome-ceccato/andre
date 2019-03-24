#!/usr/bin/env python3

import asyncio
import discord
import random
from functools import reduce
from discord import enums
from discord.ext import commands
from utils import shared
from commands import admin, birthday

class Background:
    def __init__(self, bot):
        self.bot = bot

    async def run_game_status(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed:
            if shared.enable_bg_game_rotation:
                await self.bot.change_presence(game=get_random_game())
            await asyncio.sleep(get_next_game_timeout())

    async def run_list_cache(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed:
            await shared.cache.preload_all()
            await asyncio.sleep(3600 * 12)

    async def update_avatar(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed:
            await asyncio.sleep(admin.change_avatar_if_needed())

    async def wish_birthday(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed:
            await asyncio.sleep(birthday.time_until_next_birthday())
            await birthday.check_birthdays(self.bot)

def get_next_game_timeout():
    return 1800 + random.randint(1, 90) * 60

def get_random_game():
    # No Game
    if random.randint(0, 8) == 0:
        return None

    # Random anime
    if random.randint(0, 3) == 0:
        lists = shared.cache.animelists.values()
        if lists:
            anime = random.choice(list(lists))
            if anime:
                choice = random.choice(anime)
                return discord.Game(name=choice.get('title', None), type=3)

    playing_statuses = [
        'with Neko-Hime',
        'with Neko-Hime ( ͡° ͜ʖ ͡°)',
        'doctor with Neko-Hime',
        'with Kaneda',
        'with Sakanya',
        'how old are you again? with Sakanya',
        'a Butter imitation game where the goal is to put a very long status and see whether or not it reaches the limit set by Discord. It would appear this is not long enough yet, but I have no idea what to write next so I will stop there.',
        'with a certain fish',
        'with a purple-eyed girl',
        'with others bots',

        'Real life simulator',
        'arm wrestling with the Vice President',
        'with Joe\'s ants',
        'with yoshiko\'s dog',
        'by myself',
        'with your waifu',
        'not an eroge',
        'Global Thermonuclear War',
        'with the nuclear codes',

        'Half-Life 3',
        'Portal 2',
        'Factorio',
        'osu!',
        'League of Legends',
        'NieR:Automata',
        'Rocket League',
        'Minecraft',
        'The Sims 3',
        'Grand Theft Auto: San Andreas',
        'Undertale',
        'World of Warcraft',
        'Fallout 3',
        'Overwatch',
        'HOMM 3',
        'Houkai 3rd',

        'Steins;Gate',
        'Danganronpa 2',
        'Kindred Spirits on the Roof',
        'Clannad',
        'Fate/Stay Night',
        'White Album 2',
        'Grisaia no Kajitsu',
        'Ao no Kanata no Four Rhythm',
        'Saya no Uta',
        'Root Double',
        'Katawa Shoujo',
        'DDLC',

        'with Monika',
        'with monika.chr',
        'ɐʞᴉuoɯ',
    ]

    streaming_statuses = [
        'Try k/help',
        'Need help? >help',
        'n:help for commands',
        'b/bob for help',
    ]

    listening_statuses = [
        'Nevereverland.mp3',
        'Million Clouds.mp3',
        'Stay Alive.mp3',
        'Tsukiakari no Michishirube.mp3',
        'Word of Dawn.mp3',
        '雨の菫青石.mp3',
        'Season.mp3',
        'イシュカン・コミュニケーション.mp3',
        'ハレルヤ☆エッサイム.mp3',
        'reino blanco.mp3',
        'キミガタメ 2016.mp3',
        'Freesia.mp3',
        'Rita - Song for friends.mp3',
        'GAMERS!.mp3',
        'My Truth.mp3',
        '打上花火.mp3',
        '僕だけの光.mp3',
        'Sunshine Pikkapika Ondo.mp3',
        'Believe in the sky.mp3',
        'Houseki no Kuni OP - Kyoumen no Nami.mp3',
        'Date A Live .mp3',
        'Rakuen Project.mp3',
        'Ebb and Flow.mp3',
        'Memoria.mp3',
        'Naked Dive.mp3',
        'A-gain.mp3',
        'Knew day.mp3',
        'My Dearest.mp3',
        'Ninelie.mp3',
        'Redo.mp3',
        'Hacking to the Gate.mp3',

        'anime music',
        '10 Hours of Soft Loli Breathing.flac',
    ]

    watching_statuses = [
        'cute_girls.mp4',
        'definitely_not_hentai.mkv',
        '[HorribleSubs] Dies Irae - 04 [1080p].mkv',

        'How to be a better bot.mkv',
        'Why is Kyou the best waifu.mkv',
        'How to cook for your human.mov',
        '01101010101011001010010111',
        'hexdecimal for dummies.mp4',
        'TV',

        'you',
        'the sky',
    ]

    items = [playing_statuses, streaming_statuses, listening_statuses, watching_statuses]

    game = random.choice(reduce((lambda a, b: a + b), items))
    type = next(iter([i for i, j in enumerate(items) if game in j]), 0)
    return discord.Game(name=game, type=type)

def setup(bot, config):
    background = Background(bot)
    bot.loop.create_task(background.run_game_status())
    if config['preload_lists']:
        bot.loop.create_task(background.run_list_cache())
    if config['update_avatar']:
        bot.loop.create_task(background.update_avatar())
    if config['wish_birthday']:
        bot.loop.create_task(background.wish_birthday())
