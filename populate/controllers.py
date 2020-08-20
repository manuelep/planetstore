# -*- coding: utf-8 -*-

from .models import db

from py4web import action, request, abort, redirect, URL, HTTP
from py4web.core import Fixture

class limit_to_local(Fixture):
    def on_request(self):
        if not request.urlparts.netloc.startswith('localhost'):
            raise HTTP(403)


@action('planet/populate/tracked_tiles')
@action.uses(limit_to_local())
def tracked_tiles():
    res = db(
        (db.tracked_tile.id>0) & \
        (db.tracked_tile.created_on==db.tracked_tile.modified_on)
    ).select()
    return {
        'type': 'FeatureCollection',
        'features': [row.feature for row in res]
    }
