# -*- coding: utf-8 -*-

# justr a dummy but useful test

if __name__=='__main__':

    from .optutils.base import Turbo
    from .populate import osm2db

    turbo = Turbo()

    lat, lon = 44.4092, 8.9326

    qconditions = [{
        "query": [[{"k": "amenity",},],],
        "distance": 200
    },]

    query = turbo.build_query(
        turbo.optimize_centralized_query(lon, lat,
            qconditions,
            # buffer=buffer
        ),
        # gtypes=gtypes
    )

    data = turbo(query)

    osm2db(data.nodes, data.ways, data.relations)
