#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mercantile as mc
from math import modf
import pyproj

BASE_DIM = 155

class Bbox(object):
    """docstring for Bbox."""

    def __init__(self, minx, miny, maxx, maxy):
        """
        minx @float : Min longitude
        miny @float : Min latitude
        maxx @float : Max longitude
        maxy @float : Max latitude
        """
        super(Bbox, self).__init__()
        self.minx = minx
        self.miny = miny
        self.maxx = maxx
        self.maxy = maxy

    def dims(self, crs="epsg:3857"):
        osmproj = pyproj.Proj(crs)
        minx, miny = osmproj(self.minx, self.miny)
        maxx, maxy = osmproj(self.maxx, self.maxy)
        # transformer = Transformer.from_crs(self.crs, crs)
        # minx, miny = transformer.transform(self.minx, self.miny)
        # maxx, maxy = transformer.transform(self.maxx, self.maxy)
        return maxx-minx, maxy-miny

    @property
    def osm(self):
        keys = ('w', 's', 'e', 'n',)
        return dict(zip(keys, map(str, (self.minx, self.miny, self.maxx, self.maxy,)))) # minx, miny, maxx, maxy

    def __repr__(self):
        return str(self.osm)


def get_base_tile(lon, lat, bdim=BASE_DIM):
    """
    lon  @float : Center longitude.
    lat  @float : Center latitude.
    bdim @float : Base time dimension in meters.

    returns:
        tt @mercantile.tile : Tile nearest to desidered dimension coontaining the
                              point of given coordinates.
        zoom_level @integer : The tile zoom level.
    """
    max_zoom_level = 30
    max_area = bdim**2
    for zoom_level in range(max_zoom_level):
        tt = mc.tile(lon, lat, zoom_level)
        bb = mc.xy_bounds(tt)
        if (bb.right-bb.left)*(bb.top-bb.bottom) < max_area:
            break
    return tt, zoom_level

def __get_box_dim(bt, dist):
    """ """

    ss = mc.xy_bounds(bt)
    b, h = ss.right-ss.left, ss.top-ss.bottom
    real_dim = min([b,h])

    fp, ip = modf(dist/real_dim)
    nn = ip + 1 if fp > 0 else ip
    return int(nn)

def tilebbox(dist, lon, lat, bdim=BASE_DIM, buffer=4, format=None):
    """
    dist     @float : Search distance.
    lon      @float : Center longitude.
    lat      @float : Center latitude.
    bdim     @float : Base time dimention in meters.
    buffer @integer : Buffer dimention in times of bdim.
    format  @string : Output format

    returns:
        upper left corner coordinates and bottom right cooodinates in terms of
        * [[minlon, maxlat], [maxlon, minlat]]
        * {'w': minlon, 's': minlat, 'e': maxlon, 'n': maxlat} in case OSM format is required
    """

    bt, _ = get_base_tile(lon, lat, bdim)

    nn = __get_box_dim(bt, dist)

    ul = mc.ul(bt.x-(nn+buffer), bt.y-(nn+buffer), bt.z)
    br = mc.ul(bt.x+(nn+buffer)+1, bt.y+(nn+buffer)+1, bt.z)

    if format is None:
        return Bbox(ul.lng, br.lat, br.lng, ul.lat)
    elif format == 'osm':
        keys = ('w', 's', 'e', 'n',)
        return dict(zip(keys, map(str, (ul.lng, br.lat, br.lng, ul.lat,)))) # minx, miny, maxx, maxy
    else:
        raise NotImplementedError

def boxtiles(dist, lon, lat, bdim=BASE_DIM, buffer=4):
    """ """
    bt, _ = get_base_tile(lon, lat, bdim)
    nn = __get_box_dim(bt, dist)//2

    for xx in range(-(nn+buffer-1), (nn+buffer+1)):
        for yy in range(-(nn+buffer-1), (nn+buffer+1)):
            yield bt.x+xx, bt.y+yy, bt.z,
    #         bounds = mc.bounds(bt.x+xx, bt.y+yy, bt.z)
    #         out[(bt.x+xx, bt.y+yy, bt.z,)] = Bbox(
    #             bounds.west,
    #             bounds.south,
    #             bounds.east,
    #             bounds.north
    #         )
    # return out
