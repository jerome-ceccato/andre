from discord.ext import commands
from enum import Enum
import discord.utils

from utils import shared

class PermissionLevel(Enum):
    Safe = 0
    UserData = 1
    Unsafe = 2

def is_owner_check(message):
    return message.author.id == shared.admin

def is_owner():
    return commands.check(lambda ctx: is_owner_check(ctx.message))

def is_banned_check(message, permission: PermissionLevel):
    if message.author.id in shared.banlist:
        return shared.banlist[message.author.id] <= permission.value
    return False

def is_banned(permission: PermissionLevel = PermissionLevel.Safe):
    return commands.check(lambda ctx: not is_banned_check(ctx.message, permission))
