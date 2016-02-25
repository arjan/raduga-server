# -*- coding: utf-8 -*-

"""
This file implements the bulk of the rainbow-finding algorithm.

Please consult README.md for an overview.
"""

import subprocess
from datetime import datetime
from glob import glob
import json
import sys
import os
import re

import pytz
import pysolar
from PIL import Image, ImageOps, ImageEnhance, ImageChops

from settings import GFS_FOLDER
import utils

logger = utils.install_logger()

try:
    from settings import GRIB2JSON_PATH
    grib2json = GRIB2JSON_PATH
except ImportError:
    grib2json = 'grib2json'


def find_rainclouds(THIS_GFS_SLUG):
    global grib2json

    THIS_GFS_FOLDER = os.path.join(GFS_FOLDER, THIS_GFS_SLUG)
    if not THIS_GFS_FOLDER:
        logger.debug("no grib files found. Run fetch.py?")
        return False

    logger.debug("starting cloud analysis with grib information from %s" % THIS_GFS_SLUG)

    DATE = datetime.strptime(THIS_GFS_SLUG, "%Y%m%d%H")       # strptime can’t handle timezones, what up with that?
    DATE = DATE.replace(tzinfo=pytz.UTC)                        # we know it’s UTC so we add that info http://stackoverflow.com/questions/7065164/how-to-make-an-unaware-datetime-timezone-aware-in-python

    logger.debug("date = {}".format(DATE))

    grib_file_path = os.path.join(THIS_GFS_FOLDER, "GFS_half_degree.%s.pwat.grib" % THIS_GFS_SLUG)
    json_file_path = os.path.join(THIS_GFS_FOLDER, "GFS_half_degree.%s.pwat.json" % THIS_GFS_SLUG)
    png_file_path  = os.path.join(THIS_GFS_FOLDER, "GFS_half_degree.%s.pwat.png" % THIS_GFS_SLUG)

    png_sun_mask_file_path                          = os.path.join(THIS_GFS_FOLDER, "GFS_half_degree.sun_mask.%s.pwat.png" % THIS_GFS_SLUG)
    png_clouds_greyscale_file_path                  = os.path.join(THIS_GFS_FOLDER, "GFS_half_degree.clouds_greyscale.%s.pwat.png" % THIS_GFS_SLUG)
    png_clouds_alpha_file_path                       = os.path.join(THIS_GFS_FOLDER, "GFS_half_degree.clouds_alpha.%s.pwat.png" % THIS_GFS_SLUG)
    png_clouds_greymasked_file_path                 = os.path.join(THIS_GFS_FOLDER, "GFS_half_degree.clouds_greymasked.%s.pwat.png" % THIS_GFS_SLUG)
    png_clouds_greymasked_before_russia_file_path   = os.path.join(THIS_GFS_FOLDER, "GFS_half_degree.clouds_greymasked.before_russia.%s.pwat.png" % THIS_GFS_SLUG)
    png_cloud_mask_file_path                        = os.path.join(THIS_GFS_FOLDER, "GFS_half_degree.cloud_mask.%s.pwat.png" % THIS_GFS_SLUG)
    png_cloud_mask_extruded_file_path               = os.path.join(THIS_GFS_FOLDER, "GFS_half_degree.cloud_mask.extruded.%s.pwat.png" % THIS_GFS_SLUG)

    russia_layer = Image.open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'russia.png'))

    if not os.path.exists(grib_file_path):
        logger.debug("expected GRIB file not foud")
        return False
    if os.path.exists(json_file_path):
        logger.debug("corresponding JSON found, skipping JSON conversion")
    else:
        logger.debug("converting GRIB into JSON file: %s" % json_file_path)
        try:
            pipe = subprocess.Popen([grib2json, '-d', '-n',
                             '-o', json_file_path,
                             grib_file_path])
        except OSError:
            logger.error("`grib2json` executable not found")
            sys.exit()
        c = pipe.wait()
        if c != 0:
            logger.error("error in JSON conversion")
            sys.exit()

    with open(json_file_path) as f:
        j = json.loads(f.read())

    # The logic of plotting the data was partly copied from the JavaScript here:
    # https://github.com/cambecc/earth/blob/e7be4d6810f211217956daf544111502fc57a868/public/libs/earth/1.0.0/products.js#L607

    header = j[0]['header']
    data   = j[0]['data']

    # the grid's origin (e.g., 0.0E, 90.0N)
    l0 = header['lo1']
    ph0 = header['la1']

    # distance between grid points (e.g., 2.5 deg lon, 2.5 deg lat)
    dl = header['dx']
    dph = header['dy']

    # number of grid points W-E and N-S (e.g., 144 x 73)
    ni = header['nx']
    nj = header['ny']

    logger.debug("read %s points" % len(data))
    logger.debug("the grids origin %sE, %sN" % (l0, ph0))
    logger.debug("distance between grid points: %s deg lon, %s deg lat" % (dl, dph))
    logger.debug("number of grid points W-E: %s, N-S: %s" % (ni, nj))

    latitude = ph0
    longitude = l0

    def prec2color(prec):
#        return int(255 - prec * 60)
        return int(255 - prec * 3)

    logger.debug("Converting data to color, and writing it to canvas")
    cloud_layer = Image.new("L", (ni, nj))
    cloud_layer.putdata(list(map(prec2color, data)))

    cloud_layer_greyscale = cloud_layer
    # Intermediary debug image:
    cloud_layer_greyscale.save(png_clouds_greyscale_file_path)

    # Output the alpha image
    alpha_layer = Image.new("LA", (ni, nj))
    alpha_layer.putdata(list(map(lambda p: (255, int(255-(255-p*6))), data)))
    alpha_layer.save(png_clouds_alpha_file_path)
    
    logger.debug("Pushing the contrast and then tresholding the clouds")
    enhancer = ImageEnhance.Contrast(cloud_layer)
    cloud_layer = enhancer.enhance(80)
    threshold = 191
    cloud_layer = cloud_layer.point(lambda p: p > threshold and 255)

    cloud_layer_greyscale.paste(cloud_layer, (0,0), cloud_layer)

    logger.debug("Calculating the solar altitudes for all combinations of latitude and longitude @ {}".format(DATE))
    #DATE = datetime(2015, 5, 24, 11, 0, 0)
    #logger.debug("{}".format(DATE))

    altitudes = []
    for j in range(nj):
        for i in range(ni):
            altitudes.append(pysolar.solar.get_altitude_fast(latitude, longitude, DATE))
            longitude += dl
        latitude += dph

    def altitude2colors(altitude):
        if 42 > altitude > 0:
            return 255
        else:
            return 0

    sun_mask = Image.new("L", (ni, nj))
    logger.debug("Calculating the colours based on the altitudes")
    colors = map(altitude2colors, altitudes)
    sun_mask.putdata(list(colors))

    sun_mask = ImageChops.offset(sun_mask, ni // 2, 0)

    # Intermediary debug image:
    sun_mask.save(png_sun_mask_file_path)

    # Calculate where the sun is in the image
    sun_i = altitudes.index(max(altitudes))
    sun_y = sun_i // ni
    sun_x = (sun_i + ni // 2) % ni
    logger.debug("Found the sun at index %s corresponding to %s, %s" % (sun_i, sun_x, sun_y))
    sun_mask.putpixel((sun_x, sun_y), 255)

    middle = ni // 2
    translate_x = middle - sun_x
    logger.debug("Moving the image %s pixels to the right to have the sun exactly in the middle" % translate_x)
    # Intermediary debug image:
    cloud_layer.save(png_cloud_mask_file_path.replace(".png", ".not-inverted.png"))

    cloud_layer = ImageChops.offset(cloud_layer, translate_x, 0)

    cloud_layer = ImageOps.invert(cloud_layer)
    cloud_layer.save(png_cloud_mask_file_path)

    logger.debug("Barrel distorting the clouds")
    barrel_distortion = "0.0 0.0 0.025 0.975 %s %s" % (sun_x + translate_x, sun_y)
    pipe = subprocess.Popen(['convert', png_cloud_mask_file_path,
                         '-virtual-pixel', 'black',
                         '-filter','point', '-interpolate', 'NearestNeighbor',
                         '-distort', 'Barrel', barrel_distortion,
                         '+antialias',
                         '-negate',
                         png_cloud_mask_extruded_file_path])
    pipe.wait()

    logger.debug("Adding the distorted clouds to the original, leaving only rainbow area")
    extruded_cloud_layer = Image.open(png_cloud_mask_extruded_file_path)
    cloud_layer.paste(extruded_cloud_layer, (0, 0), extruded_cloud_layer)

    logger.debug("Moving the image back to its original position")
    cloud_layer = ImageChops.offset(cloud_layer, translate_x * -1, 0)

    # Intermediary debug image:
    cloud_layer.save(png_file_path.replace(".png", ".without-sun-mask.png"))
    logger.debug("Masking where it is night or where the sun is too high to see rainbows")
    cloud_layer.paste(ImageOps.invert(sun_mask), (0, 0), ImageOps.invert(sun_mask))

    # Intermediary debug image:
    #cloud_layer.save(png_clouds_greymasked_before_russia_file_path)
    #logger.debug("Showing only rainbows over Russian soil")
    #cloud_layer.paste(russia_layer, (0, 0), russia_layer)

    logger.debug("Written cloud layer image file")
    cloud_layer.save(png_file_path)

    cloud_layer_greyscale.paste(ImageOps.invert(sun_mask), (0, 0), ImageOps.invert(sun_mask))
    #cloud_layer_greyscale.paste(russia_layer, (0, 0), russia_layer)
    cloud_layer_greyscale.save(png_clouds_greymasked_file_path)

    pipe = subprocess.Popen(['./vector.sh', THIS_GFS_SLUG,])
    pipe.wait()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # specify one ar more slugs in the form YYYYMMDDHH as command line arguments
        for slug in sys.argv[1:]:
            find_rainclouds(slug)
    else:
        # This is the default behaviour
        # Goes back in time tho find the most recent unprocessed grib file
        logger.debug('looking for forecasts to process')
        for f in sorted(os.listdir(GFS_FOLDER), reverse=True):
            slug = f
            path = os.path.join(GFS_FOLDER, slug)
            if re.match(r'\d{10}', slug) and os.path.isdir(path):
                if len(glob(os.path.join(path, '*pwat.png'))) > 0:
                    logger.debug("encountered already processed forecast %s, stop searching for forecasts" % slug)
                    break
                if len(glob(os.path.join(path, '*pwat.grib'))) > 0:
                    logger.debug("encountered forecast %s, start processing" % slug)
                    find_rainclouds(slug)
