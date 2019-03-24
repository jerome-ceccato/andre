#!/usr/bin/env python3

import asyncio
import discord
import re
from discord.ext import commands

import googletrans

from kanji_to_romaji import kanji_to_romaji
from utils import shared, utils, checks

moonrunes_auto_channel = utils.read_property('moonrunes_auto_channel')

class Languages:
    def __init__(self, bot):
        self.bot = bot

    async def on_message(self, message):
        if message.author != self.bot.user:
            if not message.content.strip().startswith(self.bot.command_prefix):
                await process_message(self.bot, message)

    @commands.command(pass_context=True, aliases=['Tr', 'translate', 'Translate'])
    @checks.is_banned(permission=checks.PermissionLevel.Unsafe)
    async def tr(self, ctx, *, content):
        split_content = content.split(' ', 1)

        if '=>' in split_content[0]:
            if split_content[0].startswith('=>'):
                langs = ['auto', split_content[0][2:]]
            else:
                split_word = split_content[0].split('=>')
                langs = [split_word[0], split_word[1]]
            content = split_content[1]
        else:
            langs = ['auto', 'en']

        try:
            message = googletrans.Translator().translate(content, dest=langs[1], src=langs[0])
            await ctx.bot.say(message.text)
        except:
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ko)

    @commands.group(pass_context=True, aliases=['Moonrunes', 'moonrune', 'Moonrune', shared.emote_wk])
    @checks.is_banned(permission=checks.PermissionLevel.Unsafe)
    async def moonrunes(self, ctx):
        if ctx.invoked_subcommand is None:
            items = ctx.message.content.split(' ', 1)
            if len(items) > 1:
                await ctx.bot.say(translate_jp(items[1].strip()))
            else:
                await translate_history(ctx.bot, ctx.message.channel)

    @moonrunes.command(pass_context=True)
    @checks.is_owner()
    async def auto(self, ctx, *, command='enable'):
        global moonrunes_auto_channel
        if command.lower() == 'enable':
            utils.write_property('moonrunes_auto_channel', ctx.message.channel.id)
            moonrunes_auto_channel = ctx.message.channel.id
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)
        elif command.lower() == 'disable':
            utils.write_property('moonrunes_auto_channel', None)
            moonrunes_auto_channel = None
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ko)

hiragana_full = '[ぁ-ゟ]'
katakana_full = '[゠-ヿ]'
kanji = '[㐀-䶵一-鿋豈-頻]'
katakana_half_width = '[｟-ﾟ]'

kanas = f'{hiragana_full}|{katakana_full}|{katakana_half_width}'
japanese = f'{kanas}|{kanji}'

def translate_jp(content):
    romaji = kanji_to_romaji(content)
    translation = googletrans.Translator().translate(content, src='ja')
    return f'`{content}` *{romaji}*\n> {translation.text}'

def percentage_of_moonrunes(content):
    total_len = len(content)
    moon_len = 0
    for block in extract_jap_block(content):
        moon_len += len(block.group(0))
    return moon_len / total_len if total_len > 0 else 0

def extract_all_translation(content):
    should_extract_all = shared.emote_wk in content
    _, message = full_extract_all_translation(content, previous_matches=[], should_extract_all=should_extract_all)
    return message

def full_extract_all_translation(content, previous_matches, should_extract_all):
    message = ''
    if percentage_of_moonrunes(content) >= 0.8:
        previous_matches.append(content)
        return previous_matches, f'{translate_jp(content)}\n'

    for block in extract_jap_block(content):
        m = block.group(0)
        if should_extract_all or not re.fullmatch(f'({kanas})+', m):
            if m not in previous_matches:
                message += f'{translate_jp(m)}\n\n'
                previous_matches.append(m)

    return previous_matches, (message if len(message) > 0 else None)

async def process_message(bot, message):
    global moonrunes_auto_channel
    if checks.is_banned_check(message, checks.PermissionLevel.Unsafe):
        return False
    if moonrunes_auto_channel and moonrunes_auto_channel == message.channel.id:
        translation = extract_all_translation(message.content)
        if translation:
            await bot.send_message(message.channel, translation)
            return True
    if bot.user.id in message.raw_mentions:
        await translate_history(bot, message.channel)
    return False

async def translate_history(bot, channel):
    output = ''
    all_matches = []
    async for message in bot.logs_from(channel, limit=10):
        if message.author != bot.user:
            if not checks.is_banned_check(message, checks.PermissionLevel.Unsafe):
                all_matches, translation = full_extract_all_translation(message.content, all_matches, should_extract_all=True)
                if translation:
                    output += translation
        else:
            if output:
                await bot.send_message(channel, output)
            return
    if output:
        await bot.send_message(channel, output)

def extract_jap_block(string):
    return re.finditer(f'({japanese})+', string)


def setup(bot):
    bot.add_cog(Languages(bot))
