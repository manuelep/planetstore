# -*- coding: utf-8 -*-

from itertools import zip_longest

# from pydal.helpers.serializers import json as jsondumps
from pydal import geoPoint
from .pgcopy import BulkCopyer
from .base import BaseParser, BaseCopier, WTF
from overpy.exception import DataIncomplete
from overpy import RelationNode, RelationWay, RelationRelation
from shapely.geometry import Point as shPoint
from shapely.geometry import Polygon as shPolygon
# from swissknife.log import timeLoggerDecorator

class MPolyRolesManager(object):
    """docstring for MPolyRolesManager."""

    def __init__(self):
        super(MPolyRolesManager, self).__init__()
        self.members = {
            "inner": [],
            "outer": []
        }
        self.geoms = {}
        self.relation = {}

    def __iter__(self):
        for o,ii in self.relation.items():
            yield o, ii

    def set_member_as(self, role, way):
        try:
            self.members[role].append(way)
        except KeyError:
            pass
        else:
            self.geoms[way.id] = shPolygon([list(map(float, (n.lon,n.lat,))) for n in way.nodes])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):

        # ~~ TODO ~~
        # WARNING! Islands within a hole are not considered at the moment.
        # Reference: http://wiki.openstreetmap.org/wiki/Relation:multipolygon
        for inner in self.members["inner"]:
            for outer in self.members["outer"]:
                if self.geoms[inner.id].within(self.geoms[outer.id]):
                    try:
                        o = self.relation[outer.id]
                    except KeyError:
                        self.relation[outer.id] = [inner.id]
                    else:
                        o.append(inner.id)


class __CommonMethods__(object):
    """docstring for __Base__."""

    def _save_way(self, info_id, way):

        if self.db.way_node(info_id=info_id) is None:
            return self.db.way_node.bulk_insert((dict(
                info_id = info_id,
                node_id =  self.cache["nodes"][node.id]["node_id"],
                sorting = sorting,
            ) for sorting, node in enumerate(way.nodes)))
        else:
            res = self.db(self.db.way_node.info_id==info_id).select(
                orderby = self.db.way_node.sorting
            )
            for srt,_dd in enumerate(zip_longest(res, way.nodes)):
                rec,node = _dd
                if node is None:
                    rec.delete_record()
                elif rec is None:
                    self.db.way_node.insert(
                        info_id = info_id,
                        node_id = self.cache["nodes"][node.id]["node_id"],
                        sorting = srt
                    )
                elif rec.node_id==self.cache["nodes"][node.id]["node_id"]:
                    # It just fix wrong values that would not exist.
                    if rec.sorting!=srt:
                        rec.update_record(sorting = srt)
                else:
                    rec.update_record(
                        node_id = self.cache["nodes"][node.id]["node_id"],
                        sorting = srt
                    )

    def parseNode(self, node):

        try:
            self.cache["nodes"][node.id]
        except KeyError:
            info_id = self._save_info(node.id,
                tags = node.tags,
                gtype = "node",
                attributes = node.attributes
            )
            coordinates = map(float, (node.lon, node.lat,))
            node_id = self._save_node(info_id, *coordinates)
            out = self.cache["nodes"][node.id] = {"id": info_id, "node_id": node_id}
            return out

    def parseWay(self, way):

        try:
            self.cache["ways"][way.id]
        except KeyError:
            info_id = self._save_info(
                way.id,
                tags = way.tags,
                gtype = "way",
                attributes = way.attributes
            )
            self._save_way(info_id, way)
            out = self.cache["ways"][way.id] = {"id": info_id}
            return out


class Parser(BaseParser, __CommonMethods__):
    """docstring for Parser."""

    def __init__(self, db, **kwargs):
        """
        db @DAL : The database in wich info, node, way_node and relation tables are defined.
        """
        super(Parser, self).__init__(db, source_name='osm')
        # Nodes and way cached by their source id
        self.cache = {"nodes": {}, "ways": {}}

    def parseRelation(self, relation):
        """

        A relation is a group of elements. To be more exact it is one of the core
        data elements that consists of one or more tags and also an ordered list
        of one or more nodes, ways and/or relations as members which is used to
        define logical or geographic relationships between other elements.
        A member of a relation can optionally have a role which describes the part
        that a particular feature plays within a relation.

        References:
            * https://wiki.openstreetmap.org/wiki/Relation
        """

        info_id = self._save_info(relation.id,
            tags = relation.tags,
            attributes = relation.attributes,
            gtype = "relation"
        )

        _relations = self.db(self.db.relation.info_id==info_id)

        if _relations.select("'0'", limitby=(0,1,), cacheable=True).first() is None:

            for member in relation.members:
                if isinstance(member, RelationWay):
                    try:
                        member_id = self.cache["ways"][member.ref]["id"]
                    except KeyError:
                        continue
                elif isinstance(member, RelationNode):
                    try:
                        member_id = self.cache["nodes"][member.ref]["id"]
                    except KeyError:
                        continue
                elif isinstance(member, RelationRelation):
                    try:
                        member_id = self.cache["relations"][member.ref]["id"]
                    except KeyError:
                        try:
                            _member = member._result.get_relation(
                                member.ref, resolve_missing=False
                            )
                        except DataIncomplete:
                            continue
                        else:
                            member_id = self.parseRelation(_member)["id"]
                else:
                    raise WTF()

                return self.db.relation.insert(info_id=info_id, member_id=member_id, role=member.role)

        else:

            # import pdb; pdb.set_trace()
            # relations = _relations(self.db.relation.member_id==self.db.info.id).select(
            #     left = self.db.relation.on(
            #         (self.db.relation.info_id == self.db.way_node.info_id) | \
            #         (self.db.relation.info_id == self.db.node.info_id)
            #     )
            # )

            # mew_members_ref = {m.ref: m for m in relation.members}

            for row in _relations(
                (self.db.relation.member_id==self.db.info.id) & \
                ~self.db.info.source_id.belongs(list(map(lambda m: str(m.ref), relation.members)))
            ).select(self.db.relation.ALL):
                row.delete_record()

            for member in relation.members:
                if isinstance(member, RelationWay):
                    try:
                        member_id = self.cache["ways"][member.ref]["id"]
                    except KeyError:
                        continue
                elif isinstance(member, RelationNode):
                    try:
                        member_id = self.cache["nodes"][member.ref]["id"]
                    except KeyError:
                        continue
                elif isinstance(member, RelationRelation):
                    try:
                        member_id = self.cache["relations"][member.ref]["id"]
                    except KeyError:
                        try:
                            _member = member._result.get_relation(
                                member.ref, resolve_missing=False
                            )
                        except DataIncomplete:
                            continue
                        else:
                            member_id = self.parseRelation(_member)["id"]
                else:
                    raise WTF()

                return self._save_relation(
                    info_id,
                    member_id,
                    role = member.role
                )

    # @timeLoggerDecorator()
    def parse(self, nodes, ways, relations):
        """ Saves overpass query result into db.

        nodes     @iterable : OSM nodes iterable
        ways      @iterable : OSM ways iterable
        relations @iterable : OSM relations iterable
        """

        # ways = nodes[0]._result.ways
        # relations = nodes[0]._result.relations

        for node in nodes:
            self.parseNode(node)

        for way in ways:
            self.parseWay(way)

        for relation in relations:
            self.parseRelation(relation)


class Copier(BaseCopier, __CommonMethods__):
    """docstring for Copier."""

    def __init__(self, db, **kwargs):
        """
        db @DAL : The database in wich info, node, way_node and relation tables are defined.
        """
        super(Copier, self).__init__(db, source_name='osm')
        # Nodes and way cached by their source id
        self.cache = {
            "nodes": kwargs.get('node', {}),
            "ways": kwargs.get('way', {}),
            "relations": kwargs.get('relation', {}),
        }

    def _save_way(self, info_id, way):

        for sorting, node in enumerate(way.nodes):
            data = dict(
                info_id = info_id,
                node_id =  self.cache["nodes"][node.id]["id"],
                sorting = sorting
            )

            self._insways.writerow(data)

    def parseRelation(self, relation):
        """ """

        try:
            info_id = self.cache["relations"][relation.id]["id"]
        except KeyError:
            info_id = self._save_info(relation.id,
                tags = relation.tags,
                attributes = relation.attributes,
                gtype = "relation"
            )

        for member in relation.members:

            if isinstance(member, RelationWay):
                try:
                    member_id = self.cache["ways"][member.ref]["id"]
                except KeyError:
                    continue
            elif isinstance(member, RelationNode):
                try:
                    member_id = self.cache["nodes"][member.ref]["id"]
                except KeyError:
                    continue
            elif isinstance(member, RelationRelation):
                try:
                    member_id = self.cache["relations"][member.ref]["id"]
                except KeyError:
                    try:
                        _member = member._result.get_relation(
                            member.ref, resolve_missing=False
                        )
                    except DataIncomplete:
                        continue
                    else:
                        member_id = self.parseRelation(_member)["id"]
            else:
                raise WTF()

            self._save_relation(info_id, member_id, role=member.role)
        out = self.cache["relations"][relation.id] = {"id": info_id}
        return out

    # @timeLoggerDecorator()
    def parse(self, nodes, ways, relations):
        """
        nodes : OSM nodes
        """

        # ways = nodes[0]._result.ways
        # relations = nodes[0]._result.relations

        with BulkCopyer(self.db.relation) as self._insrelation, \
            BulkCopyer(self.db.way_node) as self._insways, \
            BulkCopyer(self.db.node) as self._insnodes, \
            BulkCopyer(self.db.info) as self._insinfo:

            # TODO: # BulkCopyer(db.filter_attribution) as self.insfilter, \

            for node in nodes:
                self.parseNode(node)

            for way in ways:
                self.parseWay(way)

            for relation in relations:
                self.parseRelation(relation)
