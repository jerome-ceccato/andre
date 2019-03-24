from sqlalchemy import *
from migrate import *

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine
    Table('user_prog_language', meta, autoload=True).drop()
    Table('prog_language', meta, autoload=True).drop()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pass
