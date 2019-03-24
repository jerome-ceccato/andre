import asyncio
import traceback
import logging
import json
import sys
import datetime

import discord
from discord.ext import commands

from utils import database, shared, utils, bot, checks

from commands import background, welcome, languages, admin

FORMAT = "%(asctime)-15s: %(message)s"
formatter = logging.Formatter(FORMAT)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)

extensions = [
    'commands.userdb',
    'commands.useraction',
    'commands.help',
    'commands.mal',
    'commands.admin',
    'commands.random',
    'commands.welcome',
    'commands.languages',
    'commands.airing',
    'commands.birthday',
    'commands.inline',
    'commands.extrassetup',
    'commands.userextras',
    'commands.admindb',
    'commands.badges',
    'commands.hidden',
    'commands.vn'
]

bot = bot.AndreBot(command_prefix='!')

def load_config():
    with open('config.json') as f:
        return json.load(f)

def main():
    config = load_config()
    logger.info("Warming up...")
    database.setup_database()

    bot.remove_command('help')

    for extension in extensions:
        try:
            bot.load_extension(extension)
            logger.info(f"{extension} loaded.")
        except Exception:
            exception = traceback.format_exc()
            logger.warning(exception)
    logger.info(f"{len(bot.cogs)} cogs across {len(bot.extensions)} extensions loaded.")

    shared.admin = config['admin']
    if 'general' in config:
        shared.general_channel = config['general']
    shared.name_restriction = utils.read_property('name_restriction', {})
    shared.enable_bg_game_rotation = utils.read_property('enable_bg_game_rotation', False)
    shared.banlist = utils.read_property('banlist', {})

    background.setup(bot, config)
    bot.run(config["OAuth_token"])

if __name__ == "__main__":
    main()
