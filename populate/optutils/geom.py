# -*- coding: utf-8 -*-

import pyproj
import geojson

base_proj = "epsg:3857"
osmproj = pyproj.Proj(base_proj)

BASE_AREA_DIMENSION = 200
MIN_INFLUENCE_DISTANCE = 200

class GeoDict2(dict):
    """docstring for GeoDict2."""

    def __init__(self, geom={}, **kw):
        super(GeoDict2, self).__init__()
        self.__geom__ = {}

        for k,v in geom.items():
            try:
                self.__setgeom__(k, v)
            except WrongGeomType:
                pass

        for k,v in kw.items():
            try:
                self.__setgeom__(k, v)
            except WrongGeomType:
                pass
            else:
                kw.pop(k)

        self.update(kw)
        assert self.__geom__, "WARNING! No valid geom provided!"

    @classmethod
    def new(cls, **kw):
        new = cls(**kw)
        return new

    def __setgeom__(self, key, value):
        if not isinstance(value, Geom):
            raise WrongGeomType("WARNING! geom must be a 'Geom' object type.")

        assert (key=="local") or key.lower().startswith("epsg:") and key.split(":")[1].isdigit(), "Please respect the CRS name nomenclature!"
        self.__geom__[key.lower()] = value

    __getattr__ = dict.__getitem__

    @property
    def geom(self):
        return self.__geom__

    @property
    def id(self):
        return self.__id__

    @property
    def properties(self):
        return {k: v for k,v in self.items()}

    def get_feature(self, crs="epsg:4326", **kw):
        try:
            feat = self.geom[crs].feature
        except KeyError:
            myproj = pyproj.Proj(crs)
            e, n = myproj(*self.geom["epsg:4326"].xy)
            geom = Point(e, n, type="EPSG", properties={'code': crs.split(":")[1]})
            feat = geom.feature
        return geojson.Feature(geometry=feat.geometry, id=self.id, properties=dict(self.properties, **kw))

    def coordinates(self, crs=base_proj):
        return self.geom[crs].coordinates

    @classmethod
    def OSMSerialfactory(cls, OSMNodes, **kw):
        for OSMNode in OSMNodes:
            yield cls.OSMfactory(OSMNode, **kw)


class Bbox(GeoDict2):
    """ """
    buffer = None

    def get_shape(self, crs=base_proj):
        """ Returns the _external polygon_ as a shapely object """
        coordinates = self.geom[crs].coordinates
        return shPolygon(coordinates[0])

    def __contains__(self, lonlat):
        crs = 'epsg:4326'
        bbox_as_shape = self.get_shape(crs)
        node_as_shape = Node.factory(*lonlat).get_shape(crs)
        return bbox_as_shape.contains(node_as_shape)


    @classmethod
    def factory(cls, minlon, minlat, maxlon, maxlat, crss=(base_proj,)):

        _crss = (crs for crs in crss if crs!="epsg:4326")

        _ring = (minlon, minlat,), \
            (maxlon, minlat,), \
            (maxlon, maxlat,), \
            (minlon, maxlat,), \
            (minlon, minlat,),

        geom = dict(Polygon.projfactory((_ring,), crs=crs) for crs in _crss)
        geom["epsg:4326"] = Polygon((_ring,))

        return cls(geom = geom)

    @classmethod
    def bufferfactory(cls, lon, lat,
        buffer = BASE_AREA_DIMENSION+MIN_INFLUENCE_DISTANCE,
        crss = (base_proj,)
    ):
        """
        lon    @float : Longitude
        lat    @float : Latitude
        buffer @float : the buffer length in meters
        crss    @list : A list of valid crs
        """
        _crss = set([crs for crs in crss if crs!="epsg:4326"] + [base_proj])

        def _ring(crs):
            myproj = pyproj.Proj(crs)
            e, n = myproj(lon, lat)
            mine = e - buffer
            maxe = e + buffer
            minn = n - buffer
            maxn = n + buffer
            return crs, ((mine, minn,), \
                (maxe, minn,), \
                (maxe, maxn,), \
                (mine, maxn,),
                (mine, minn,),)

        # import pdb; pdb.set_trace()
        geom = dict([Polygon.factory((_r,), crs=_crs) for _crs,_r in ((a,b) for a,b in (_ring(crs) for crs in _crss))])

        myproj = pyproj.Proj(_crs)
        minlon, minlat = myproj(*map(min, zip(*_r)), inverse=True)
        maxlon, maxlat = myproj(*map(max, zip(*_r)), inverse=True)
        _ring = (minlon, minlat,), \
            (maxlon, minlat,), \
            (maxlon, maxlat,), \
            (minlon, maxlat,), \
            (minlon, minlat,),
        geom["epsg:4326"] = Polygon((_ring,))
        bbox_new = cls.new(geom=geom)
        bbox_new.buffer = buffer
        return bbox_new

    def min(self, crs="epsg:4326"):
        return tuple(map(min, zip(*self.geom[crs].coordinates[0])))

    def max(self, crs="epsg:4326"):
        return tuple(map(max, zip(*self.geom[crs].coordinates[0])))

    def center_and_max_dist(self, crs="epsg:3857"):
        mine, minn = self.min(crs)
        maxe, maxn = self.max(crs)
        dmax = max([maxe-mine, maxn-minn])/2
        center = Node.enfactory(mine+(maxe-mine)/2, minn+(maxn-minn)/2)
        return center, dmax

    @property
    def minlon(self):
        return self.min(crs="epsg:4326")[0]

    @property
    def minlat(self):
        return self.min(crs="epsg:4326")[1]

    @property
    def maxlon(self):
        return self.max(crs="epsg:4326")[0]

    @property
    def maxlat(self):
        return self.max(crs="epsg:4326")[1]

    def _lbrt(self, crs="epsg:4326"):
        """ """
        minx, miny = self.min(crs=crs)
        maxx, maxy = self.max(crs=crs)
        return minx, miny, maxx, maxy

    @property
    def lbrt(self):
        return self._lbrt(crs="epsg:4326")

    def _nsew(self, crs="epsg:4326"):
        minx, miny, maxx, maxy = self._lbrt(crs=crs)
        return maxy, miny, maxx, minx

    @property
    def nsew(self):
        return self._nsew(crs="epsg:4326")

    @property
    def osmbbox(self):
        values = self.lbrt
        keys = ("w", "s", "e", "n",)
        return dict(zip(keys, map(str, values)))

    def split(self, n=10):
        incr = self.buffer * 2 / float(n)
        first = incr/2.
        coordinates = self.coordinates()[0][0]
        cellcoords = []
        side = first
        for i in range(n):
            for j in range(n):
                est, nord = osmproj( coordinates[0] + first + (incr*i), coordinates[1] + first + (incr*j) , inverse=True)
                yield Bbox.bufferfactory(est, nord, side)

class Geom(object):

    known_crs = {
        # * http://spatialreference.org/ref/sr-org/7483/
        # Projection used in many popular web mapping applications (Google/Bing/OpenStreetMap/etc).
        # Sometimes known as EPSG:900913.
        "epsg:3857": {"link": {
            "href": "http://spatialreference.org/ref/sr-org/7483/proj4/",
            "type": "proj4"
        }}
    }

    def __init__(self, feature):
        validation = geojson.is_valid(feature)
        assert validation['valid']=='yes', validation['message']
        super(Geom, self).__init__()
        self.feature = feature

    __repr__ = lambda self: self.feature.__repr__()

    __str__ = __repr__

    @property
    def geometry(self):
        return self.feature["geometry"]

    geom = geometry

    def __call__(self):
        return self.geom

    @property
    def crs(self):
        return self.feature.get("crs")

    def extract(self):
        """ Extracts basic components """
        return self.feature["crs"], self.feature["geometry"]

    @property
    def coordinates(self):
        return tuple(self.feature["geometry"]["coordinates"])


class Polygon(Geom):

    def __init__(self, rings, properties=None, type="link"):
        """
        rings @list/@tuple : List of rings part of the polygon;
            for Polygons with multiple rings, the first must be the exterior
            ring and any others must be interior rings or holes.
        properties @dict : CRS properties
        type @str : Type of CRS propeties informations
        """
        kw = {} if properties is None else {"crs": {"type": type, "properties": properties}}
        self.feature = geojson.Feature(
            geometry = geojson.Polygon(rings),
            **kw
        )

    @classmethod
    def factory(cls, rings, crs=base_proj):
        """ """
        _type, props = list(cls.known_crs[crs].items())[0]
        return crs,  cls(rings, properties=props, type=_type)

    @classmethod
    def projfactory(cls, _rings, crs=base_proj, **kw):
        """
        Build projected polygon starting from rings or sequences of vertices
        in longitude and latitude.
        _rings @list : List of longitude and latitude coordinates;
        crs  @string : Name of the desidered crs
        """
        custom_proj = pyproj.Proj(crs)
        try:
            _type = kw["type"]
            props = kw["properties"]
        except KeyError:
            _type, props = list(cls.known_crs[crs].items())[0]

        rings = tuple(map(
            lambda ring: tuple(map(
                lambda coords: custom_proj(*coords),
                ring
            )),
            _rings
        ))
        return crs, cls(rings, properties=props, type=_type)

class Bbox(GeoDict2):
    """ """
    buffer = None

    def get_shape(self, crs=base_proj):
        """ Returns the _external polygon_ as a shapely object """
        coordinates = self.geom[crs].coordinates
        return shPolygon(coordinates[0])

    def __contains__(self, lonlat):
        crs = 'epsg:4326'
        bbox_as_shape = self.get_shape(crs)
        node_as_shape = Node.factory(*lonlat).get_shape(crs)
        return bbox_as_shape.contains(node_as_shape)


    @classmethod
    def factory(cls, minlon, minlat, maxlon, maxlat, crss=(base_proj,)):

        _crss = (crs for crs in crss if crs!="epsg:4326")

        _ring = (minlon, minlat,), \
            (maxlon, minlat,), \
            (maxlon, maxlat,), \
            (minlon, maxlat,), \
            (minlon, minlat,),

        geom = dict(Polygon.projfactory((_ring,), crs=crs) for crs in _crss)
        geom["epsg:4326"] = Polygon((_ring,))

        return cls(geom = geom)

    @classmethod
    def bufferfactory(cls, lon, lat,
        buffer = BASE_AREA_DIMENSION+MIN_INFLUENCE_DISTANCE,
        crss = (base_proj,)
    ):
        """
        lon    @float : Longitude
        lat    @float : Latitude
        buffer @float : the buffer length in meters
        crss    @list : A list of valid crs
        """
        _crss = set([crs for crs in crss if crs!="epsg:4326"] + [base_proj])

        def _ring(crs):
            myproj = pyproj.Proj(crs)
            e, n = myproj(lon, lat)
            mine = e - buffer
            maxe = e + buffer
            minn = n - buffer
            maxn = n + buffer
            return crs, ((mine, minn,), \
                (maxe, minn,), \
                (maxe, maxn,), \
                (mine, maxn,),
                (mine, minn,),)

        # import pdb; pdb.set_trace()
        geom = dict([Polygon.factory((_r,), crs=_crs) for _crs,_r in ((a,b) for a,b in (_ring(crs) for crs in _crss))])

        myproj = pyproj.Proj(base_proj)
        minlon, minlat = myproj(*map(min, zip(*_ring(base_proj)[1])), inverse=True)
        maxlon, maxlat = myproj(*map(max, zip(*_ring(base_proj)[1])), inverse=True)
        _ring = (minlon, minlat,), \
            (maxlon, minlat,), \
            (maxlon, maxlat,), \
            (minlon, maxlat,), \
            (minlon, minlat,),
        geom["epsg:4326"] = Polygon((_ring,))
        bbox_new = cls.new(geom=geom)
        bbox_new.buffer = buffer
        return bbox_new

    def min(self, crs="epsg:4326"):
        return tuple(map(min, zip(*self.geom[crs].coordinates[0])))

    def max(self, crs="epsg:4326"):
        return tuple(map(max, zip(*self.geom[crs].coordinates[0])))

    def center_and_max_dist(self, crs="epsg:3857"):
        mine, minn = self.min(crs)
        maxe, maxn = self.max(crs)
        dmax = max([maxe-mine, maxn-minn])/2
        center = Node.enfactory(mine+(maxe-mine)/2, minn+(maxn-minn)/2)
        return center, dmax

    @property
    def minlon(self):
        return self.min(crs="epsg:4326")[0]

    @property
    def minlat(self):
        return self.min(crs="epsg:4326")[1]

    @property
    def maxlon(self):
        return self.max(crs="epsg:4326")[0]

    @property
    def maxlat(self):
        return self.max(crs="epsg:4326")[1]

    def _lbrt(self, crs="epsg:4326"):
        """ """
        minx, miny = self.min(crs=crs)
        maxx, maxy = self.max(crs=crs)
        return minx, miny, maxx, maxy

    @property
    def lbrt(self):
        return self._lbrt(crs="epsg:4326")

    def _nsew(self, crs="epsg:4326"):
        minx, miny, maxx, maxy = self._lbrt(crs=crs)
        return maxy, miny, maxx, minx

    @property
    def nsew(self):
        return self._nsew(crs="epsg:4326")

    @property
    def osmbbox(self):
        values = self.lbrt
        keys = ("w", "s", "e", "n",)
        return dict(zip(keys, map(str, values)))

    def split(self, n=10):
        incr = self.buffer * 2 / float(n)
        first = incr/2.
        coordinates = self.coordinates()[0][0]
        cellcoords = []
        side = first
        for i in range(n):
            for j in range(n):
                est, nord = osmproj( coordinates[0] + first + (incr*i), coordinates[1] + first + (incr*j) , inverse=True)
                yield Bbox.bufferfactory(est, nord, side)
