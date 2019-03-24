from sqlalchemy import *
from migrate import *

meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine
    user = Table('user', meta, autoload=True)

    badge = Table(
        'badge', meta,
        Column('id', Integer, primary_key=True),
        Column('description', String(1000)),
        Column('link', String(1000), nullable=True)
    )
    badge.create()

    user_badge = Table(
        'user_badge', meta,
        Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
        Column('badge_id', Integer, ForeignKey('badge.id'), primary_key=True),
        Column('timestamp', Integer)
    )
    user_badge.create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pass
