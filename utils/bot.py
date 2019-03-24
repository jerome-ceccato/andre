import asyncio

import discord
from discord.ext import commands

class AndreBot(commands.Bot):
    @asyncio.coroutine
    def send_message(self, destination, content=None, *, tts=False, embed=None):
        if content is not None:
            return super(AndreBot, self).send_message(destination, content=_limit_content(content), tts=tts, embed=embed)
        elif embed is not None:
            return super(AndreBot, self).send_message(destination, content=content, tts=tts, embed=_limit_embed(embed))
        else:
            return super(AndreBot, self).send_message(destination, content=content, tts=tts, embed=embed)

def _limit_content(content):
    return _force_max_size(content, limit=2000)

def _limit_embed(embed):
    embed.title = _force_max_size(embed.title, limit=256)
    embed.description = _force_max_size(embed.description, limit=2048)

    return embed

def _force_max_size(string, limit, end_string = '[...]'):
    if not string:
        return string
    if len(string) > limit:
        string = string[:limit - len(end_string)] + end_string
    return string

class SubcommandMessage(discord.Message):
    def __init__(self, message: discord.Message):
        super(discord.Message, self).__init__()

        for attribute in message.__slots__:
            setattr(self, attribute, getattr(message, attribute, None))

