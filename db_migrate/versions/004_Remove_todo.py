from sqlalchemy import *
from migrate import *

meta = MetaData()

todo = Table(
    'todo', meta,
    Column('id', Integer, primary_key=True),
    Column('content', String(4000)),
    Column('from_discord_id', String(100))
)

def upgrade(migrate_engine):
    meta.bind = migrate_engine
    todo.drop()


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    todo.create()
