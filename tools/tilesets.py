# -*- coding: utf-8 -*-

import mercantile as mt
import h3
from shapely.geometry import Point
import pyproj

BASE_DIM = 155 # meters
MT_MAX_ZOOM = 30
H3_MAX_ZOOM = 15

def mt_tile_by_dim(lon, lat, bdim=BASE_DIM, asc=True):
    """
    lon  @float : Center longitude.
    lat  @float : Center latitude.
    bdim @float : Base tile dimension in meters.

    returns:
        tt @mercantile.tile : Tile nearest to desidered dimension coontaining the
                              point of given coordinates.
        zoom_level @integer : The tile zoom level.
    """
    max_area = bdim**2

    zooms = range(MT_MAX_ZOOM) if asc else reversed(range(MT_MAX_ZOOM))
    for zoom_level in zooms:
        tt = mt.tile(lon, lat, zoom_level)
        bb = mt.xy_bounds(tt)
        if (bb.right-bb.left)*(bb.top-bb.bottom) < max_area:
            if asc:
                break
        elif not asc:
            break
    return tt

def h3_tile_by_dim(lon, lat, bdim=BASE_DIM, asc=True):

    osmproj = pyproj.Proj("epsg:3857")

    resolutions = range(H3_MAX_ZOOM) if asc else reversed(range(H3_MAX_ZOOM))
    for resolution in resolutions:
        tile = h3.geo_to_h3(lat, lon, resolution)
        polygon = h3.h3_to_geo_boundary(tile)

        x1, y1 = osmproj(*polygon[0])
        x2, y2 = osmproj(*polygon[1])

        dist = Point(x1, y1).distance(Point(x2, y2))

        if (asc and dist < bdim) or (not asc and dist > bdim):
            break

    return tile

def tile_by_dim(lon, lat, bdim=BASE_DIM, asc=True, classic=False):
    if classic:
        return mt_tile_by_dim(lon, lat, bdim=bdim, asc=asc)
    else:
        return h3_tile_by_dim(lon, lat, bdim=bdim, asc=asc)
