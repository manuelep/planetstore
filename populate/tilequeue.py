# -*- coding: utf-8 -*-

from .models import db
import datetime

now = lambda: datetime.datetime.utcnow()

populate_query = (db.tracked_tile.created_on==db.tracked_tile.modified_on)

update_query = lambda :( db.tracked_tile.modified_on<(now()-datetime.timedelta(days=28*6)))

def __reserve_tiles(query, n=10):
    """ """

    res = db(
        query & \
        ~db.tracked_tile.id.belongs(db(db.queued_tile)._select(db.queued_tile.tile_id))
        # (db.tracked_tile.id!=db.queued_tile.tile_id)
    ).select(
        db.tracked_tile.id,
        limitby = (0,n,),
        orderby = (db.tracked_tile.modified_on|db.tracked_tile.id)
    )

    def _loopOtiles():
        for row in res:
            yield db.queued_tile.insert(tile_id=row.id)

    out = list(_loopOtiles())
    db.commit()
    return out

def reserve_tiles_for_populate(n=10):
    return __reserve_tiles(populate_query, n=n)

def reserve_tiles_for_update(n=10):
    return __reserve_tiles(update_query(), n=n)

def free_tiles(qid, *qids):
    """ """
    db(db.queued_tile.id.belongs((qid,)+qids)).delete()
    db.commit()

def queued_dbset(qid, *qids):
    """ """

    dbset = db(db.tracked_tile.id.belongs(
        db(db.queued_tile.id.belongs((qid,)+qids))._select(db.queued_tile.tile_id)
    ))

    return dbset
