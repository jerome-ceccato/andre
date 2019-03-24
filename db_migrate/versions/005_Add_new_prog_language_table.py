from sqlalchemy import *
from migrate import *

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine
    user = Table('user', meta, autoload=True)

    prog = Table(
        'user_programming_language', meta,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer, ForeignKey(user.c.id)),
        Column('name', String(100)),
        Column('extra', String(200))
    )
    prog.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    user = Table('user', meta, autoload=True)

    prog = Table(
        'user_programming_language', meta,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer, ForeignKey(user.c.id)),
        Column('name', String(100)),
        Column('extra', String(200))
    )
    prog.drop()
