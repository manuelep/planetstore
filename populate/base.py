# -*- coding: utf-8 -*-

from pydal.helpers.serializers import serializers
jsondumps = serializers.json

from pydal import geoPoint
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

_get_coordinates = lambda lon, lat, height=None: (lon, lat,) if height is None else (lon, lat, height,)

class PanicError(Exception):
    """ """
    def __init__(self, message="/o\ It should never happen, why does it happen? /o\ "):
        super(PanicError, self).__init__(message)


class WTF(PanicError):
    """docstring for WTF."""


class __Base__(object):
    """docstring for __Base__."""

    def __init__(self, db, source_name):
        """
        db @DAL : The database in wich info, node, way_node and relation tables are defined.
        source_name @string : Source name
        """
        super(__Base__, self).__init__()
        self.db = db
        self.source_name = source_name


class BaseParser(__Base__):
    """docstring for BaseParser."""

    # def save_addon(self, key, properties):
    #     """ """
    #     ref_value = properties[key]
    #     rec = self.db.addon(
    #         source_name = self.source_name,
    #         ref_key = key,
    #         ref_value = ref_value
    #     )
    #     if rec is None:
    #         addon_id = db.addon.insert(
    #             properties = jsondumps(properties),
    #             ref_key = key,
    #             ref_value = ref_value,
    #             source_name = self.source_name,
    #         )
    #     else:
    #         raise NotImplementedError()
    #
    # def save_addons(self, key, addons):
    #     """ """

    def _save_info(self, rec_or_sid, gtype, tags=None, properties=None, attributes=None, merge=False):
        """
        rec    @row :
        sid @string : The entity identifier restricted to the data source environment.
        tags  @dict :
        """

        def insert_or_update(tags, properties, attributes, rec=None, **kw):
            if rec is None:
                id = self.db.info.insert(
                    tags = tags,
                    properties = properties,
                    attributes = attributes,
                **kw)
            elif not merge:
                rec.update_record(
                    tags = tags,
                    properties = properties,
                    attributes = attributes,
                **kw)
                id = rec.id
            else:
                rec.update_record(
                    tags = None if (rec.tags is None and tags is None) else dict(rec.tags or {}, **(tags or {})),
                    properties = None if (rec.properties is None and properties is None) else dict(rec.properties or {}, **(properties or {})),
                    attributes = None if (rec.attributes is None and attributes is None) else dict(rec.attributes or {}, **(attributes or {})),
                **kw)
                id = rec.id
            logger.debug(f"Inserted info record with id: {id}")
            return id

        if not hasattr(rec_or_sid, "update_record"):
            # rec_or_sid is just an id
            sid = str(rec_or_sid)
            flt = dict(
                source_name = self.source_name,
                gtype = gtype,
                source_id = sid
            )
            rec = self.db.info(**flt)
            if not rec is None:
                if not attributes or rec.attributes.get('changeset')!=attributes.get('changeset'):
                    return insert_or_update(tags, properties, attributes, rec=rec, **flt)
                else:
                    return rec.id
            else:
                return insert_or_update(tags, properties, attributes, rec=rec, **flt)

        else:
            # rec_or_sid is a db record
            rec=rec_or_id

            if not attributes or rec.attributes.get('changeset')!=attributes.get('changeset'):
                return insert_or_update(tags, properties, attributes, rec=rec)

    def _save_node(self, info_id, *coordinates):
        """
        info_id @integer :
        coordinates @tuple : lon, lat, height (optional)
        """
        point = geoPoint(*_get_coordinates(*coordinates))
        rec = self.db.node(info_id=info_id)

        if rec is None:
            return self.db.node.insert(info_id=info_id, geom=point)
        else:
            rec.update_record(geom=point)
            return rec.id

    def _save_way_node(self, info_id, node_id, sorting):
        rec = self.db.way_node(info_id=info_id, node_id=node_id)
        if rec is None:
            return self.db.way_node.insert(info_id=info_id, node_id=node_id, sorting=sorting)
        else:
            if rec.sorting!=sorting:
                rec.update_record(sorting=sorting)
                return rec.id

    def _save_relation(self, info_id, member_id, role):
        rec = self.db.relation(info_id=info_id, member_id=member_id)
        if rec is None:
            return self.db.relation.insert(info_id=info_id, member_id=member_id, role=role)
        else:
            rec.update_record(role=role)
            return rec.id


def normalize_tags_for_db(kwargs):
    _main = lambda c: (c[0], c[1] if not isinstance(c[1], str) else c[1].replace('"', "'"),)
    return dict(map(_main, kwargs.items()))


class BaseCopier(__Base__):
    """docstring for BaseCopier."""

    def _save_info(self, sid, gtype, tags=None, properties=None, attributes=None):
        """
        sid @string : The entity identifier restricted to the data source environment.
        tags  @dict : OSM like tags
        properties @dict : Original raw properties
        attributes  @dict : OSM like attributes
        """

        _suid = dict(
            source_name = self.source_name,
            gtype = gtype,
            source_id = sid,
        )

        timestamp = datetime.now()

        flt = dict(
            _suid,
            tags = 'NULL' if tags is None else jsondumps(normalize_tags_for_db(tags)),
            properties = 'NULL' if properties is None else jsondumps(properties),
            attributes = 'NULL' if attributes is None else jsondumps(attributes),
            suid = self.db.info.suid.compute(_suid),
            created_on = timestamp,
            modified_on = timestamp
        )

        info_id = self._insinfo.writerow(flt)
        # TODO: forse
        # for
        # self.insfilter(dict(
        #
        # ))
        return info_id

    def _save_node(self, info_id, *coordinates):
        """
        info_id @integer :
        """
        point = geoPoint(*_get_coordinates(*coordinates))
        return self._insnodes.writerow(dict(
            info_id = info_id,
            geom = "SRID=4326;{}".format(point)
        ))

    def _save_way_node(self, info_id, node_id, sorting):
        return self._insways.writerow(dict(info_id=info_id, node_id=node_id, sorting=sorting))

    def _save_relation(self, info_id, member_id, role):
        # suid = self.db.relation.suid.compute(vars()),
        return self._insrelation.writerow(dict(
            info_id = info_id,
            member_id = member_id,
            role = role,
            # suid = suid
        ))
