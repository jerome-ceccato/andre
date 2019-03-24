#!/usr/bin/env python3

import discord
from utils import cached_data, bot_state

reaction_ok = '✅'
reaction_ko = '❌'
reaction_notfound = '❓'
reaction_forbidden = '⛔'

emote_xinil = '<:xinil:342392066418147339>'
emote_kanna = '<:kanna:335316999569670145>'
emote_humm = '<:humm:332142122700505088>'
emote_wk = '<:wk:349938858143645696>'
emote_tada = '🎉'

main_server_id = '343060137164144642'
general_channel = '343060137164144642'
birthday_blacklist = ['172153939838500865']

foxy_id = '242276581039538178'

mal_embed_link_template = ' https://www.malembed.tk/<username>'

admin = ''
version = '0.77'
cache = cached_data.CachedData()
state = bot_state.BotState()
name_restriction = {}
banlist = {}

enable_bg_game_rotation = False
