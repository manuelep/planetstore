"""
This is an optional file that defined app level settings such as:
- database settings
- session settings
- i18n settings
This file is provided as an example:
"""
import os

# db settings
# DB_URI = "postgres://username:password@localhost/test"
DB_POOL_SIZE = 10
DB_MIGRATE = False

# try import private settings
try:
    from .settings_private import *
except ModuleNotFoundError:
    pass
