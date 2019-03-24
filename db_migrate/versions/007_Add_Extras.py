from sqlalchemy import *
from migrate import *

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine
    user = Table('user', meta, autoload=True)

    extras = Table(
        'extras', meta,
        Column('id', Integer, primary_key=True),
        Column('question', String(1000)),
        Column('options', String(1000), nullable=True)
    )
    extras.create()

    user_extras = Table(
        'user_extras', meta,
        Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
        Column('extras_id', Integer, ForeignKey('extras.id'), primary_key=True),
        Column('response', String(1000))
    )
    user_extras.create()

def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pass
