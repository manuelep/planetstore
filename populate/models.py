# -*- coding: utf-8 -*-

import mercantile as mc

from .tools import get_uri
from ..models import db
from .tile import boxtiles

from py4web import Field
import datetime

now = lambda: datetime.datetime.utcnow()

db.define_table("tracked_tile",
    Field('xtile', 'integer', required=True, notnull=True),
    Field('ytile', 'integer', required=True, notnull=True),
    Field('zoom', 'integer', required=True, notnull=True, default=18),
    Field('uri', required=False, unique=True, notnull=True,
        compute = lambda row: get_uri(row['xtile'], row['ytile'], row['zoom'])
    ),
    # Field('filled', 'boolean', default=False),
    Field('created_on', 'datetime',
        # required = True,
        notnull = True,
        default = now,
        writable = False, readable = True
    ),
    Field('modified_on', 'datetime',
        # required = True, # notnull=True,
        update = now,
        default = now,
        # compute = lambda _=None: now(),
        writable = False, readable = True
    ),
    Field("is_active", "boolean", default=True, readable=False, writable=False),
    # Field('task_id', "reference scheduler_task", notnull=True, requires=None),
    Field.Virtual('feature', lambda row: mc.feature(
        mc.quadkey_to_tile(mc.quadkey(row.tracked_tile.xtile, row.tracked_tile.ytile, row.tracked_tile.zoom)),
        fid = row.tracked_tile.uri,
        props = {'created': row.tracked_tile.created_on, 'updated': row.tracked_tile.modified_on}
    )),
    # Field.Virtual('last_update', lambda row: get_last_update(row.tile.uri))
)

db.define_table("queued_tile",
    Field("tile_id", "reference tracked_tile", unique=True)
)

def track_tiles(lon, lat, maxdist, buffer=4):
    """ """

    tiles = list(boxtiles(maxdist, lon, lat, buffer=buffer))

    get_uri = lambda x, y, z: db.tracked_tile.uri.compute({'xtile': x, 'ytile': y, 'zoom': z})
    _tiles_i_got = db(
        db.tracked_tile.uri.belongs(map(lambda xyz: get_uri(*xyz), tiles))
    ).select()

    tiles_i_got = {r.uri: r for r in _tiles_i_got}

    _d = lambda xtile, ytile, zoom: vars()

    def _loopOtiles():
        for xtile, ytile, zoom in tiles:
            myuri = get_uri(xtile, ytile, zoom)
            if not myuri in tiles_i_got:
                yield db.tracked_tile.insert(**_d(xtile, ytile, zoom))
            # elif tiles_i_got[myuri].last_update is None:
            #     yield tiles_i_got[myuri].id

    return {
        'new': list(_loopOtiles()),
        'old': [row.id for row in _tiles_i_got],
        'tiles': tiles
    }

# if __name__=='__main__':
#     track_tiles(8.938015, 44.405762, 0)
#     import pdb; pdb.set_trace()
