# -*- coding: utf-8 -*-

from ..models import db

from geojson import Point, Feature, FeatureCollection
from itertools import groupby
from .gjson import NodeParser, PolygonParser, WayParser
from .gjson import NodeCopier, PolygonCopier, WayCopier
from .osm import Parser, Copier
try:
    from ujson import loads as jsloads
except ImportError:
    from json import loads as jsloads

from tqdm import tqdm

def feat(feature, source_name='__GENERIC__', copy=False, **kw):
    data = jsloads(feature) if isinstance(feature, str) else feature
    if not copy:
        if 'merge' in kw:
            merge = kw.pop('merge')
        else:
            merge = False
        if feature['geometry']['type']=='Point':
            node_parser = NodeParser(db, source_name, **kw)
            return node_parser.parse_feature(feature, merge=merge)
        elif feature['geometry']['type']=='Polygon':
            polygon_parser = PolygonParser(db, source_name, **kw)
            return polygon_parser.parse_feature(feature, merge=merge)
        else:
            NotImplementedError()
    else:
        if feature['geometry']['type']=='Point':
            node_parser = NodeCopier(db, source_name, **kw)
            return node_parser.parse_feature(feature)
        elif feature['geometry']['type']=='Polygon':
            polygon_parser = PolygonCopier(db, source_name, **kw)
            return polygon_parser.parse_feature(feature)
        else:
            NotImplementedError()
    raise NotImplementedError()

def json(collection, source_name='__GENERIC__', copy=False, **kw):
    data = jsloads(collection) if isinstance(collection, str) else collection
    grouping = lambda feat: feat['geometry']['type']
    data_by_type = groupby(sorted(data['features'], key=grouping), key=grouping)
    if copy:
        node_parser = NodeCopier(db, source_name, **kw)
        polygon_parser = PolygonCopier(db, source_name, **kw)
        linestring_parser = WayCopier(db, source_name, **kw)
    else:
        node_parser = NodeParser(db, source_name, **kw)
        polygon_parser = PolygonParser(db, source_name, **kw)
        linestring_parser = WayParser(db, source_name, **kw)

    for tt, features in data_by_type:
        if tt=='Point':
            node_parser.parse(features)
        elif tt=='Polygon':
            polygon_parser.parse(features)
        elif tt == 'LineString':
            linestring_parser.parse(features)
        else:
            raise NotImplementedError

geojson = json

def osm(nodes, ways, relations, copy=True, **kw):

    if copy:

        values = [
            db.info.suid.compute(
                {'source_name': 'osm', 'gtype': 'node', 'source_id': nn.id}
            ) for nn in nodes]

        values += [
            db.info.suid.compute(
                {'source_name': 'osm', 'gtype': 'way', 'source_id': nn.id}
            ) for nn in ways]

        values += [
            db.info.suid.compute(
                {'source_name': 'osm', 'gtype': 'relation', 'source_id': nn.id}
            ) for nn in relations]

        # data_to_insert = deepcopy(data)
        # data_to_update =

        res = db(
            db.info.suid.belongs(values)
        ).select(
            db.info.id,
            db.info.gtype,
            db.info.source_id
        ).group_by_value(db.info.gtype)

        already_in_db = {
            k: {int(row.source_id): row for row in rows} \
                for k,rows in res.items()
        }

        def is_not_in_db(k):

            try:
                myobjs = already_in_db[k]
            except KeyError:
                return lambda _: True
            else:
                return lambda nn: not str(nn.id) in myobjs

        Copier(db, source_name='OSM', **already_in_db).parse(
            nodes = filter(is_not_in_db('node'), nodes),
            ways = filter(is_not_in_db('way'), ways),
            relations = filter(is_not_in_db('relation'), relations)
        )

    else:

        Parser(db, source_name='OSM', **kw).parse(
            nodes = nodes,
            ways = ways,
            relations = relations
        )

def idealista(cls, elementList, copy=False):
    def to_geojson():
        """ """
        for element in elementList:
            point = Point([element.pop('longitude'), element.pop('latitude')])
            yield Feature(geometry=point, properties=element, id=element['propertyCode'])

    return json(FeatureCollection(to_geojson()), source_name='idealista', copy=copy)
