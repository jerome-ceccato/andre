#!/usr/bin/env python3

import asyncio
import discord
import datetime
import subprocess
from discord.ext import commands

from utils import database, shared, checks, utils

class AdminDB:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def backupdb(self, ctx):
        if 0 == backup_db():
            await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)


    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def purgedb(self, ctx, mal_name, field_name):
        session = database.new_session()
        user = session.query(database.User).filter(database.User.mal_name == mal_name).first()

        if not user:
            user = session.query(database.User).filter(database.User.discord_id == mal_name).first()
            if not user:
                await ctx.bot.say(f"No user found for name \"{mal_name}\"")
                return

        if field_name == '*':
            backup_db(extra_name=f'-purge-{mal_name}-{field_name}')
            db_remove_user(session, user)
            session.commit()
        elif field_name in ['mal_name', 'gender', 'birthdate', 'bio', 'timezone']:
            backup_db(extra_name=f'-purge-{mal_name}-{field_name}')
            setattr(user, field_name, None)
            session.commit()
        elif field_name == 'languages':
            backup_db(extra_name=f'-purge-{mal_name}-{field_name}')
            db_remove_language(session, user)
            session.commit()
        elif field_name == 'prog_languages':
            backup_db(extra_name=f'-purge-{mal_name}-{field_name}')
            db_remove_prod_language(session, user)
            session.commit()
        elif field_name == 'projects':
            backup_db(extra_name=f'-purge-{mal_name}-{field_name}')
            db_remove_projects(session, user)
            session.commit()
        elif field_name == 'extras':
            backup_db(extra_name=f'-purge-{mal_name}-{field_name}')
            db_remove_extras(session, user)
            session.commit()
        else:
            await ctx.bot.say(f'Unrecognized field "{field_name}"')
            return

        await ctx.bot.add_reaction(ctx.message, shared.reaction_ok)

    @commands.group(pass_context=True)
    @checks.is_banned(permission=checks.PermissionLevel.Safe)
    async def db(self, ctx):
        pass

    @db.command(pass_context=True)
    async def users(self, ctx, fmt='{0}:{1}'):
        session = database.new_session()
        users = session.query(database.User).all()

        message = ''
        for user in users:
            message += fmt.format(user.discord_id, user.mal_name) + '\n'
        await ctx.bot.say(f'```{message}```')

def backup_db(extra_name = ''):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    pull = subprocess.run(['cp', 'data/users.db', f'data/backup/users-{current_time}{extra_name}.db'], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, encoding='utf8')
    print(pull.stdout)

    return pull.returncode

def db_remove_extras(session, user):
    extras = session.query(database.UserExtras).filter(database.UserExtras.user_id == user.id).all()
    for extra in extras:
        session.delete(extra)

def db_remove_language(session, user):
    for language in user.languages:
        session.delete(language)

def db_remove_prod_language(session, user):
    for language in user.prog_languages:
        session.delete(language)

def db_remove_projects(session, user):
    projects = user.projects
    to_remove = []
    for project in projects:
        owner = session.query(database.User).filter(database.User.projects.any(database.Project.id == project.id)).all()
        if not owner or (len(owner) == 1 and owner[0].id == user.id):
            to_remove.append(project)
    user.projects[:] = []
    for project in to_remove:
        session.delete(project)

def db_remove_user(session, user):
    db_remove_extras(session, user)
    db_remove_language(session, user)
    db_remove_prod_language(session, user)
    db_remove_projects(session, user)

    if len(session.query(database.User).filter(database.User.country_id == user.country_id).all()) <= 1:
        session.delete(user.country)

    session.delete(user)

def setup(bot):
    bot.add_cog(AdminDB(bot))
