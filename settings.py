# -*- coding: utf-8 -*-

"""
This is an optional file that defined app level settings such as:
- database settings
- session settings
- i18n settings
This file is provided as an example:
"""

from ..settings import DB_URI
from ..settings import DB_MIGRATE
from ..settings import DB_POOL_SIZE
from ..settings import DB_FOLDER

DB_SHARED = True

# If you need a separete database just add a parallel settings_private.py file
# with the following assigned variables adapted to your needs:
"""
# -*- coding: utf-8 -*-
# db settings
DB_SHARED = False
DB_URI = "postgres://<PG user>:<password>@<host name>/<db name>"
DB_POOL_SIZE = <int>
DB_MIGRATE = <True/False>
"""

# try import private settings
try:
    from .settings_private import *
except ModuleNotFoundError:
    pass
