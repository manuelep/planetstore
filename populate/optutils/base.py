# -*- coding: utf-8 -*-

import os
import hashlib
import geojson
import overpy
from lxml import etree
from itertools import groupby
from time import sleep
from datetime import datetime
from functools import reduce
from urllib.request import urlopen
from urllib.error import HTTPError

from .geom import Bbox, BASE_AREA_DIMENSION
from ...tools.tile import BASE_DIM, tilebbox

class MaxRetriesReached(overpy.exception.OverPyException):
    """ Courtesy of: https://github.com/DinoTools/python-overpy/blob/31c6e689c0d49d6617e020597914f47a0bc98f04/overpy/exception.py#L40
    Raised if max retries reached and the Overpass server didn't respond with a result.
    """
    def __init__(self, retry_count, exceptions):
        self.exceptions = exceptions
        self.retry_count = retry_count

    def __str__(self):
        return "Unable get any result from the Overpass API server after %d retries." % self.retry_count


overpy.exception.MaxRetriesReached = MaxRetriesReached
overpy.Overpass.default_max_retry_count = 3
overpy.Overpass.default_retry_timeout = 10
# overpy.Overpass.max_retry_count = 5
overpy.Overpass.retry_timeout = 10

class Turbo(object):
    """ OSM Overpass Turbo utils """

    default_base_resource_path = ""

    def __init__(self, *args, **kw):
        self.__cache__ = {}
        self.api = overpy.Overpass(*args, **kw)

    def __raw_call__(self, query):
        """ Reimplements the call to Overpass Turbo web service for DEBUG purposes only.
        Courtesy of: https://github.com/DinoTools/python-overpy/blob/4b5ace5baf854dd84dbfea955d0c67f602bd754d/overpy/__init__.py#L113
        Query the Overpass API
        :param String|Bytes query: The query string in Overpass QL
        :return: The parsed result
        :rtype: overpy.Result
        """

        try:
            max_retry_count = self.api.max_retry_count
        except AttributeError:
            max_retry_count = self.api.default_max_retry_count

        try:
            retry_timeout = self.api.retry_timeout
        except AttributeError:
            retry_timeout = self.api.default_retry_timeout

        read_chunk_size = 4096

        if not isinstance(query, bytes):
            query = query.encode("utf-8")

        retry_num = 0
        retry_exceptions = []
        do_retry = True if max_retry_count > 0 else False
        while retry_num <= max_retry_count:
            if retry_num > 0:
                sleep(retry_timeout)
            retry_num += 1
            t0 = datetime.now()
            try:
                f = urlopen(self.api.url, query)
            except HTTPError as e:
                f = e
            else:
                dt = datetime.now()-t0

            response = f.read(read_chunk_size)
            while True:
                data = f.read(read_chunk_size)
                if len(data) == 0:
                    break
                response = response + data
            f.close()

            if f.code == 200:

                if PY2:
                    http_info = f.info()
                    content_type = http_info.getheader("content-type")
                else:
                    content_type = f.getheader("Content-Type")

                if content_type in ("application/json", "application/osm3s+xml",):
                    return response, dt

                e = overpy.exception.OverpassUnknownContentType(content_type)
                if not do_retry:
                    raise e
                retry_exceptions.append(e)
                continue

            if f.code == 400:
                e = overpy.exception.OverpassBadRequest(query, msgs=None)
                if not do_retry:
                    raise e
                retry_exceptions.append(e)
                continue

            if f.code == 429:
                e = overpy.exception.OverpassTooManyRequests
                if not do_retry:
                    raise e
                retry_exceptions.append(e)
                continue

            if f.code == 504:
                e = overpy.exception.OverpassGatewayTimeout
                if not do_retry:
                    raise e
                retry_exceptions.append(e)
                continue

        raise overpy.exception.MaxRetriesReached(retry_count=retry_num, exceptions=retry_exceptions)

    def __fake_call__(self, query, *args, **kw):
        """ Caches responses for DEBUG purposes only """

        queryhash = hashlib.new('sha224')
        queryhash.update(query)
        querychecksum = queryhash.hexdigest()

        rp = os.path.join(self.default_base_resource_path, "resources", querychecksum)

        resource_file = os.path.normpath(rp)

        if not os.path.isfile(resource_file):
            if not os.path.exists(os.path.dirname(resource_file)):
                try:
                    os.makedirs(os.path.dirname(resource_file))
                except OSError as exc: # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise

            raw_data, dt = self.__raw_call__(query)

            if not raw_data is None:
                with open(resource_file, "w") as res:
                    res.write(raw_data)
            data_dim = os.stat(resource_file).st_size
            delta_sec = dt.total_seconds()
            logger.info("Retrieved {} bytes in {} seconds (at a speed of {} Bps)".format(
                data_dim, delta_sec,
                data_dim/delta_sec
            ))

        assert os.path.isfile(resource_file), "File Not Found!"
        with open(resource_file, mode='rb') as myxml:
            body = myxml.read()
        return self.api.parse_json(body) #.nodes

    def __call__(self, query, *args, **kw):
        """
        query @string : The OSM query ready to be submitted to the Overpass web service.
        """

        queryhash = hashlib.new('sha224')
        queryhash.update(query)
        querychecksum = queryhash.hexdigest()

        try:
            response = self.__cache__[querychecksum]["response"]
            assert not response is None, "This should never happen, why it happens?"
        except (KeyError, AssertionError,):
            for t in range(1, 4):
                try:
                    response = self.api.query(query, *args, **kw) #.nodes
                    assert not response is None, "This should never happen, why it happens?"
                except (
                    overpy.exception.OverpassTooManyRequests,
                    overpy.exception.OverpassGatewayTimeout,
                    AssertionError,
                ):
                    sleep(t*overpy.Overpass.retry_timeout)
                    continue
                else:
                    self.__cache__[querychecksum] = {
                        "response": response,
                        "query": query
                    }
                    return self.__cache__[querychecksum]["response"]
            raise
        else:
            return response # self.__cache__[querychecksum]["response"]

    def nodes(self, *args, **kw):
        return self(*args, **kw)

    @staticmethod
    def build_query(qconditions, gtypes=None, timeout=60, pretty_print=False, maxsize=None):
        """ Returns the Overpass turbo query in XML format
        qconditions  @list : Query conditions;
        gtypes       @list : One or more values between 'node', 'way', 'relation';
        timeout   @int/str : The query timeout;
        pretty_print @bool : If true returns the indented XML output for debug purposes.

        Examples:

        qconditions = [{
            "query": [[{"k": ..., "modv": ..., "v/regv": ...}, ...], ...],
            "distance": 0,
            "gtypes": [...], # Optional. Possible values: "node", "way", "relation"
            # "amplitude": 0,
            "newer": "%Y-%m-%ddT%H:%M:%SZ" #
        }]
        """

        default_gtype_values = ("node", "way", "relation",)

        def __check__(geom):
            msg_template = "{geom} is not a valid OSM entity type (possible values are: {geoms})."
            gtypes
            assert (geom in default_gtype_values), msg_template.format(
                geom = geom,
                geoms = ','.join(default_gtype_values)
            )

        if gtypes is None:
            gtypes = ("node",)
        else:
            map(__check__, gtypes)

        Root = etree.Element(
            "osm-script",
            output = "json",
            timeout = "{0:d}".format(timeout),
            **{"element-limit": maxsize for x in 'a' if not maxsize is None}
        )
        Union = etree.SubElement(Root, "union", into="_")

        _recurse = {
            "way": ["down"],
            "relation": ["up"]
        }

        def _append(gtype, query, bbox, newer_than=None):
            for _union in query:
                Query = etree.SubElement(Union, "query", into="_", type=gtype)
                for _intersection in _union:
                    etree.SubElement(Query, "has-kv", **_intersection)
                if not newer_than is None:
                    etree.SubElement(Query, "newer", than=newer_than)
                for recurse_type in _recurse.get(gtype, []):
                    etree.SubElement(Union, "recurse", into="_", type=recurse_type, **{"from": "_"})
                etree.SubElement(Query, "bbox-query", **bbox)

        for cond in qconditions():
            try:
                _gtypes = cond.pop('gtypes')
            except KeyError:
                _gtypes = gtypes

            for _type in _gtypes:
                _append(_type, **cond)

        etree.SubElement(Root, "print",
            e="",geometry="skeleton", limit="", mode="meta", n="", order="id", s="", w="",
            **{"from": "_"}
        )
        return etree.tostring(Root, pretty_print=pretty_print)

    @staticmethod
    def optimize_centralized_query_by_base_tile(lon, lat, qconditions, bdim=BASE_DIM, buffer=3, newer_than=None):
        """
        lon @float :
        lat @float :
        qconditions  @list : Query conditions given by distance from point;
        bdim @float : Base tile dimention;
        buffer @integer : Number of buffer tiles;
        newer_than @string : "%Y-%m-%dT%H:%M:%SZ"

        Examples:

        qconditions = [{
            "query": [[{"k": ..., "modv": ..., "v/regv": ...}, ...], ...],
            "distance": ...,
            "gtypes": [...], # Optional. Possible values: "node", "way", "relation", "way-node", node-relation", "relation-way", "relation-relation", "relation-backwards"
            ""
        }, ...]
        """

        grouping_func = lambda cnd: (int(cnd['distance']//bdim), cnd['gtypes'],)

        def _main():
            _grouped_queryes_ = groupby(sorted(qconditions, key=grouping_func), key=grouping_func)
            for gd, _cnds in _grouped_queryes_:
                _dist, gtypes = gd
                max_dist = (_dist+1)*bdim
                bbox = tilebbox(max_dist, lon, lat, bdim=bdim, buffer=buffer, format='osm')
                allcnds = reduce(lambda a,b: a+b, (tuple(i["query"]) for i in _cnds))
                yield {
                    "bbox": bbox,
                    "query": tuple(dict([(tuple(map(lambda j: tuple(j.items()), i)), i,) for i in allcnds]).values()),
                    "gtypes": gtypes,
                    "newer_than": newer_than
                }

        return _main

    @staticmethod
    def optimize_centralized_query(lon, lat, qconditions, buffer=None):
        """
        qconditions  @list : Query conditions given by distance from point;

        Examples:

        qconditions = [{
            "query": [[{"k": ..., "modv": ..., "v/regv": ...}, ...], ...],
            "distance": ...
        }, ...]
        """

        def _main():

            _grouped_queryes_ = groupby(
                qconditions,
                key = lambda cnd: float("{distance:d}".format(**cnd))
            )

            for gd, _cnds in _grouped_queryes_:
                cnds = (tuple(i["query"]) for i in _cnds)
                allcnds = sum(cnds, ())
                yield {
                    "bbox": Bbox.bufferfactory(
                        lon=lon, lat=lat, crss=("epsg:4326",),
                        buffer = gd + (buffer if not buffer is None else BASE_AREA_DIMENSION)
                    ).osmbbox,
                    "query": tuple(dict([(tuple(map(lambda j: tuple(j.items()), i)), i,) for i in allcnds]).values())
                }

        return _main

    def iter(self, lon, lat, qconditions, buffer=None, gtypes=None, **kw):
        """ """
        query = self.build_query(
            self.optimize_centralized_query(lon, lat,
                qconditions,
                buffer=buffer
            ),
            gtypes=gtypes
        )
        return self(query, **kw)

    @staticmethod
    def check(tags, k, modv=None, **kw):
        """
        Evalluates whether the OSM node properties respect the single filter condition.
        Returns boolean.

        properties @dict : The node tags (at leas object must support __getitem__);
        k        @string : The OSM Overpass Turbo condition tag key;
        modv     @string : The OSM Overpass Turbo condition operator (None/"not").
                           If modv is None a value for "regv" must be provided
                           (NOTE: at the moment the only supported value for
                           "regv" is the wildcard ".")
        v        @string : (If provided) is the OSM Overpass Turbo queried tag value.

        || WARNINNG! It's a very raw implementation but enough good for       ||
        || our actual purposes.                                               ||
        """

        def _check():

            try:
                rvalue = tags[k]
            except KeyError:
                return False
            else:
                try:
                    cvalue = kw["v"]
                except KeyError:
                    try:
                        cvalue = kw["regv"]
                    except KeyError:
                        return True
                    else:
                        if cvalue==".":
                            return True
                        else:
                            raise NotImplementedError("Filter not yet supported.")
                else:
                    return not cvalue or cvalue==rvalue

        if not modv:
            return _check()
        elif modv=="not":
            return not _check()
        else:
            raise NotImplementedError("Operator not yet supported")
