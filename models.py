# -*- coding: utf-8 -*-

from .common import db, T
from py4web import Field

import datetime

now = lambda : datetime.datetime.utcnow()

class Info(Field):
    """ """

    def __init__(self, fieldname='info_id', type='reference info',
        *args, **kwargs):
        super(Info, self).__init__(fieldname, type, *args, **kwargs)


db.define_table("info",
    Field("source_name", required=True, notnull=True),
    Field("source_id", required=True, notnull=True),
    Field("properties", "json", required=True, notnull=False,
        label = "External properties",
        comment = "External properties as they come from source"
    ),
    Field('created_on', 'datetime',
        default = now,
        writable=False, readable=False,
        label = T('Created On')
    ),
    Field('modified_on', 'datetime',
        update=now, default=now,
        writable=False, readable=False,
        label=T('Modified On')
    ),
    Field("tags", "json", label='OSM tags', required=False, notnull=False),
    Field("attributes", "json", rname="attrs", label='OSM meta attributes', required=False, notnull=False),
    Field("gtype", label=T('Geometry type'), # notnull=True,
        writable=False, readable=True
    ),
    Field("suid", unique=True, required=True, notnull=True,
        compute = lambda r: "{source_name}-{gtype}-{source_id}".format(**r)
    ),
    Field("is_active", "boolean", default=True, update=True)
)

db.define_table("node",
    Info(),
    Field("geom", "geometry()")
)

db.define_table("way_node",
    Info(),
    Field("node_id", "reference node", notnull=True),
    Field("sorting", "integer", default=0, notnull=True, writable=False, readable=False),
)

db.define_table("relation",
    Info(),
    Field("member_id", "reference info", notnull=True),
    Field("role"),
)

db.define_table("data_source",
    Field("source_name"),
    migrate = False
)
