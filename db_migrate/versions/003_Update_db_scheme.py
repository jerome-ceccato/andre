from sqlalchemy import *
from migrate import *

meta = MetaData()

user_language = Table(
    'user_language', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('user.id')),
    Column('code', String(3)),
    Column('extra', String(200))
)

def upgrade(migrate_engine):
    meta.bind = migrate_engine
    user = Table('user', meta, autoload=True)
    user.c.age.drop()

    language = Table('language', meta, autoload=True)
    language.drop()

    assoc_language = Table('user_language', meta, autoload=True)
    assoc_language.drop()

    birthdate = Column('birthdate', String(10), nullable=True)
    birthdate.create(user)

    country = Table('country', meta, autoload=True)
    country.c.name.alter(Column('code', String(3)))

    user_language.create()

def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pass
