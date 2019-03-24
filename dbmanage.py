#!/usr/bin/env python
from migrate.versioning.shell import main

if __name__ == '__main__':
    main(repository='db_migrate', url='sqlite:///data/users.db', debug='False')
