# -*- coding: utf-8 -*-

import math

from settings import *

"""
These functions allow to deal with an OpenStreetMap style map
"""

def deg2px(lat_deg, lon_deg, zoom=4):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom * 256
    xpx = int((lon_deg + 180.0) / 360.0 * n)
    ypx = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return (xpx, ypx)

def num2deg(xtile, ytile, zoom=4):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

def px2deg(x, y, zoom=4):
    global TILE_SIZE
    xtile = x / float(TILE_SIZE) + 0.5 / TILE_SIZE
    ytile = y / float(TILE_SIZE) + 0.5 / TILE_SIZE
    return num2deg(xtile, ytile, zoom)

"""
These functions deal with the data we get from the Global Forecast system:

the grids origin 0.0E, 90.0N
distance between grid points: 0.5 deg lon, 0.5 deg lat
number of grid points W-E: 720, N-S: 361
"""

def point_to_position(point):
    return (int(point[0] * .5), int(point[1] * -.5 + 90))

def position_to_point(position):
    return (int(position[0] * 2), int((position[1] - 90) * -2))
