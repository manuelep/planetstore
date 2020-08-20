# -*- coding: utf-8 -*-

from .populate.optutils.base import Turbo

def filter2query(tags):
    """
    tags @list : ex.: [{key: value, ...}, ...]
    """
    return [[{"k": k, "v": v} for k,v in tags_.items()] for tags_ in tags]


def tags2turbo(lon, lat, dist, bdim=155, timeout=60, pretty_print=False, maxsize=None, tags=[]):
    """ """
    gtypes = ('node', 'way', 'relation',)
    turbo = Turbo()
    qconditions = [{
        "query": filter2query(tags),
        "distance": dist,
        "gtypes": gtypes, # Optional. Possible values:
        #   "node", "way", "relation", "way-node", node-relation",
        #   "relation-way", "relation-relation", "relation-backwards"
        # "amplitude": 0,
        "newer": "%Y-%m-%ddT%H:%M:%SZ" #
    }]
    query = turbo.build_query(
        Turbo.optimize_centralized_query_by_base_tile(lon, lat, qconditions, bdim=bdim),
        timeout=timeout, maxsize=maxsize
    )
    return dict(query=query)
