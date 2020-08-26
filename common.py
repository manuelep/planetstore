# -*- coding: utf-8 -*-

from . import settings

if not settings.DB_SHARED:
    from ..common import T
    from py4web import DAL
    # connect to db
    db = DAL(settings.DB_URI,
        folder = settings.DB_FOLDER, pool_size=settings.DB_POOL_SIZE, migrate=settings.DB_MIGRATE,
        lazy_tables=False, check_reserved=False
    )
else:
    from ..common import db, T
    db._check_reserved = False

# from ..settings import DB_FOLDER
# from py4web import DAL
# # from ..common import T
#
# # connect to db
# db = DAL(settings.DB_URI,
#     folder=DB_FOLDER, pool_size=settings.DB_POOL_SIZE, migrate=settings.DB_MIGRATE,
#     lazy_tables=False, check_reserved=False
# )
