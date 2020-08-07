# -*- coding: utf-8 -*-

from .populate.optutils.base import Turbo

def tags2turbo(lon, lat, tags=[], timeout=60, pretty_print=False, maxsize=None):
    """ """
    gtypes = ('node', 'way', 'relation',)
    turbo = Turbo()
    qconditions = [{
        "query": [[{"k": k, "v": v},] for k,v in tags],
        "distance": 0,
        "gtypes": gtypes, # Optional. Possible values:
        #   "node", "way", "relation", "way-node", node-relation",
        #   "relation-way", "relation-relation", "relation-backwards"
        # "amplitude": 0,
        "newer": "%Y-%m-%ddT%H:%M:%SZ" #
    }]
    query = turbo.build_query(
        Turbo.optimize_centralized_query_by_base_tile(lon, lat, qconditions),
        timeout=timeout, pretty_print=pretty_print, maxsize=maxsize
    )
    return dict(query=query)
