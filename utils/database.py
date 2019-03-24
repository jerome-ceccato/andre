import os
import sys
from sqlalchemy import Table, Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()

user_project_association_table = Table('user_project', Base.metadata,
    Column('user_id', Integer, ForeignKey('user.id')),
    Column('project_id', Integer, ForeignKey('project.id'))
)

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    discord_id = Column(String(100))
    mal_name = Column(String(250), nullable=True)
    gender = Column(String(250), nullable=True)
    birthdate = Column(String(10), nullable=True)
    bio = Column(String(4000), nullable=True)
    timezone = Column(String(250), nullable=True)
    country_id = Column(Integer, ForeignKey('country.id'))
    country = relationship('Country')
    languages = relationship('Language')
    prog_languages = relationship('ProgrammingLanguage')
    projects = relationship('Project', secondary=user_project_association_table)

class Project(Base):
    __tablename__ = 'project'

    id = Column(Integer, primary_key=True)
    name = Column(String(250))
    description = Column(String(1000))
    link = Column(String(250), nullable=True)

class Country(Base):
    __tablename__ = 'country'

    id = Column(Integer, primary_key=True)
    code = Column(String(3))

class Language(Base):
    __tablename__ = 'user_language'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    code = Column(String(3))
    extra = Column(String(200))

class ProgrammingLanguage(Base):
    __tablename__ = 'user_programming_language'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    name = Column(String(100))
    extra = Column(String(200))

class Extras(Base):
    __tablename__ = 'extras'

    id = Column(Integer, primary_key=True)
    question = Column(String(1000))
    options = Column(String(1000), nullable=True)

class UserExtras(Base):
    __tablename__ = 'user_extras'

    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)
    extras_id = Column(Integer, ForeignKey('extras.id'), primary_key=True)
    response = Column(String(1000))

class Badge(Base):
    __tablename__ = 'badge'

    id = Column(Integer, primary_key=True)
    description = Column(String(1000))
    link = Column(String(1000), nullable=True)

class UserBadge(Base):
    __tablename__ = 'user_badge'

    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)
    badge_id = Column(Integer, ForeignKey('badge.id'), primary_key=True)
    timestamp = Column(Integer)

##########################################

def setup_database():
    engine = create_engine('sqlite:///data/users.db', encoding='utf-8')
    Base.metadata.create_all(engine)

def new_session():
    engine = create_engine('sqlite:///data/users.db', encoding='utf-8')
    Base.metadata.bind = engine
    Session = sessionmaker(bind=engine)
    return Session()
