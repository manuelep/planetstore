# -*- coding: utf-8 -*-

from swissknife.py4web import brap, LocalsOnly
from py4web import action, request, abort, redirect, URL, HTTP

from ..common import unauthenticated #, db, session, T, cache, auth, logger, authenticated
from .callbacks import tags2turbo as tags2turbo_

#@unauthenticated()
@action('planet/tags2turbo', method=['GET','POST'])
@action.uses('generic.xml')
def tags2turbo():
    res = brap()(tags2turbo_)()
    return dict(body=res['query'])
