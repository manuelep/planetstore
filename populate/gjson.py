# -*- coding: utf-8 -*-

from pydal import geoPoint
from .pgcopy import BulkCopyer
from .base import WTF, BaseParser, BaseCopier
from hashids import Hashids
myhashids = Hashids()


class __CommonMethods__(object):
    """docstring for __FeatureParser__."""

    def parse_feature(self, feature):
        """ """
        method_name = feature["geometry"]["type"]
        try:
            method = getattr(self, "_parse{}".format(method_name))
        except (AttributeError, NotImplementedError,) as err:
            raise NotImplementedError(feature["geometry"]["type"])
        else:
            info_id = method(feature)
            if info_id is None:
                # import pdb; pdb.set_trace()
                raise WTF()

            return info_id


class NodeParser(BaseParser, __CommonMethods__):
    """docstring for GeojsonParser."""

    def __init__(self, db, source_name, tags_on_update="replace", properties_on_update="replace"):
        """
        db @DAL : The database in wich info, node, way_node and relation tables are defined.
        source_name @string : Source name
        tags_on_update @string : Supported values:
            - "replace": Replace tags
            - "update": Update tags
        properties_on_update @string : See tags_on_update.
        """
        super(NodeParser, self).__init__(db, source_name)
        self.tags_on_update = tags_on_update
        self.properties_on_update = properties_on_update

    def _parsePoint(self, feature):
        """ """
        info_id = self._save_info(feature["id"],
            gtype = 'node',
            tags = feature.get('tags'),
            properties = feature["properties"]
        )
        coordinates = feature["geometry"]["coordinates"]
        node_id = self._save_node(info_id, *coordinates)
        return info_id

    def parse_features(self, features):
        """
        features api:
            Standard geojson feature with additional optional property "tags"
            i.e.: {
              "type": "Feature",
              "geometry": {
                "type": "Point",
                "coordinates": [125.6, 10.1]
              },
              "properties": {
                "name": "Dinagat Islands"
              },
              "tags": {"<tag name>": <tag value>} # OPTIONAL NON STANDARD
            }
        """
        for feature in features:
            info_id = self.parse_feature(feature)

    parse = parse_features


class WayParser(NodeParser):

    def _save_way(self, info_id, feat_id, coordinates, wn=0):
        for sorting, xy in enumerate(coordinates):
            nsid = '{}-{}'.format(feat_id, myhashids.encode(wn, sorting))
            node_info_id = self._save_info(nsid, gtype='node')
            node_id = self._save_node(node_info_id, *xy)
            data = dict(info_id=info_id, node_id=node_id, sorting=sorting)
            self._save_way_node(**data)

    def _parseWay(self, feature):

        info_id = self._save_info(
            feature["id"],
            tags = feature.get('tags'),
            properties = feature['properties'],
            gtype="way"
        )

        if feature['geometry']['type']=='LineString':
            self._save_way(info_id, feature["id"], feature["geometry"]['coordinates'])
        elif feature['geometry']['type']=='Polygon':
            self._save_way(info_id, feature["id"], feature["geometry"]['coordinates'][0])
            crdlen = len(feature["geometry"]['coordinates'])

        return info_id

    _parseLineString = _parseWay


class PolygonParser(WayParser):

    def _parseMultiPolygon(self, feature):

        info_id = self._save_info(
            feature["id"],
            tags = dict(feature.get('tags', {}), type='multipolygon'),
            properties = feature['properties'],
            gtype="relation"
        )

        for wn,waynodes in enumerate(feature["geometry"]['coordinates']):
            swid = '{}-{}'.format(feature["id"], myhashids.encode(wn))
            way_info_id = self._save_info(swid, gtype='way')
            self._save_way(way_info_id, swid, waynodes, wn=wn)

            self._save_relation(
                info_id, way_info_id,
                role = 'outer' if wn==0 else 'inner'
            )

        return info_id

    def _parsePolygon(self, feature):
        """ """

        check = len(feature["geometry"]['coordinates'])
        if check == 1:
            gtype = 'way'
        elif check > 1:
            gtype = 'relation'
        else:
            raise ValueError

        if gtype=='way':
            info_id = self._parseWay(feature)
        # gtype == 'relation'
        else:
            info_id = self._parseMultiPolygon(feature)

        return info_id


class NodeCopier(BaseCopier, __CommonMethods__):
    """docstring for NodeCopier."""

    def _parsePoint(self, feature):
        """ """
        info_id = self._save_info(feature["id"],
            gtype = 'node',
            tags = feature.get('tags'),
            properties = feature["properties"]
        )
        node_id = self._save_node(info_id, *feature["geometry"]["coordinates"])
        return info_id

    def parse(self, features):
        """
        features api:
            Standard geojson feature with additional optional property "tags"
            i.e.: {
              "type": "Feature",
              "geometry": {
                "type": "Point",
                "coordinates": [125.6, 10.1]
              },
              "properties": {
                "name": "Dinagat Islands"
              },
              "tags": {"<tag name>": <tag value>} # OPTIONAL NON STANDARD OSM LIKE TAGS
            }
        """

        with BulkCopyer(self.db.node) as self._insnodes, \
            BulkCopyer(self.db.info) as self._insinfo:

            for feature in features:
                info_id = self.parse_feature(feature)


class WayCopier(NodeCopier, WayParser):
    """ """

    def parse(self, features):
        """
        features api:
            Standard geojson feature with additional optional property "tags"
            i.e.: {
              "type": "Feature",
              "geometry": {
                "type": "Point",
                "coordinates": [125.6, 10.1]
              },
              "properties": {
                "name": "Dinagat Islands"
              },
              "tags": {"<tag name>": <tag value>} # OPTIONAL NON STANDARD OSM LIKE TAGS
            }
        """

        with BulkCopyer(self.db.way_node) as self._insways, \
            BulkCopyer(self.db.node) as self._insnodes, \
            BulkCopyer(self.db.info) as self._insinfo:

            for feature in features:
                info_id = self.parse_feature(feature)


class PolygonCopier(WayCopier, PolygonParser):
    """docstring for PolygonCopier."""

    # def _parseMultiPolygon(self, feature):
    #
    #
    # def _parsePolygon(self, feature):
    #     """ """
    #
    #     check = len(feature["geometry"]['coordinates'])
    #     if check == 1:
    #         gtype = 'way'
    #     elif check > 1:
    #         gtype = 'relation'
    #     else:
    #         raise ValueError
    #
    #     # info_id = self.save_info(
    #     #     feature["id"],
    #     #     feature["properties"],
    #     #     gtype = gtype
    #     # )
    #
    #     _info_ = lambda **kw: dict(
    #         sid = feature["id"],
    #         gtype = gtype,
    #         tags = dict(feature.get('tags', {}), **kw) or None,
    #         properties = feature['properties']
    #     )
    #
    #     if gtype=='way':
    #         info_id = self._save_info(**_info_())
    #         for sorting, xy in enumerate(feature["geometry"]['coordinates'][0]):
    #
    #             nsid = '{}-{}'.format(feature["id"], myhashids.encode(0, sorting))
    #
    #             node_info_id = self._save_info(nsid, gtype='node')
    #             node_id = self._save_node(node_info_id, *xy)
    #             data = dict(
    #                 info_id = info_id,
    #                 node_id =  node_id,
    #                 sorting = sorting
    #             )
    #             self._insways.writerow(data)
    #     # gtype == 'relation'
    #     else:
    #         try:
    #             info_id = self._save_info(**_info_(type='multipolygon'))
    #         except Exception as err:
    #             import pdb; pdb.set_trace()
    #         for wn,waynodes in enumerate(feature["geometry"]['coordinates']):
    #
    #             wsid = '{}-{}'.format(feature["id"], myhashids.encode(wn))
    #             way_info_id = self._save_info(wsid, gtype='way')
    #
    #             if wn == 0:
    #                 data = dict(info_id=info_id, member_id=way_info_id, role='outer')
    #                 self._insrelation.writerow(dict(
    #                     suid = self.db.relation.suid.compute(data),
    #                     **data
    #                 ))
    #                 # self._insrelation.writerow(dict(info_id=info_id, way_id=way_info_id, outer_way_id="NULL"))
    #                 # _outer_way_id=int(way_info_id)
    #             else:
    #                 data = dict(info_id=info_id, member_id=way_info_id, role='inner')
    #                 self._insrelation.writerow(dict(
    #                     suid = self.db.relation.suid.compute(data),
    #                     **data
    #                 ))
    #                 # self._insrelation.writerow(dict(info_id=info_id, way_id=way_info_id, outer_way_id=_outer_way_id))
    #
    #             for sorting, xy in enumerate(waynodes):
    #                 nsid = '{}-{}'.format(feature["id"], myhashids.encode(wn, sorting))
    #                 assert nsid
    #                 node_info_id = self._save_info(nsid, gtype='node')
    #                 node_id = self._save_node(node_info_id, *xy)
    #                 data = dict(
    #                     info_id = way_info_id,
    #                     node_id =  node_id,
    #                     sorting = sorting
    #                 )
    #                 self._insways.writerow(data)
    #
    #     return info_id

    def parse(self, features):
        """
        features api:
            Standard geojson feature with additional optional property "tags"
            i.e.: {
              "type": "Feature",
              "geometry": {
                "type": "Point",
                "coordinates": [125.6, 10.1]
              },
              # OPTIONAL NON STANDARD OSM LIKE TAGS
              "properties": {"name": "Dinagat Islands"},
              # STANDARD OSM LIKE TAGS
              "tags": {"<tag name>": <tag value>}
            }
        """

        with BulkCopyer(self.db.relation) as self._insrelation, \
            BulkCopyer(self.db.way_node) as self._insways, \
            BulkCopyer(self.db.node) as self._insnodes, \
            BulkCopyer(self.db.info) as self._insinfo:

            for feature in features:
                info_id = self.parse_feature(feature)
