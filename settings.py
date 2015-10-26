# -*- coding: utf-8 -*-

import os
import re
import sys
from glob import glob
from datetime import datetime

import pytz

SERVER_NAME = '127.0.0.1:5000'

"""
WEATHER RESOURCES SETTINGS
"""

def relative_folder(*parts):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), *parts)


GFS_FOLDER = relative_folder('static', 'gfs')


# This is to find the latest folder of the form 2014022100
def get_latest_gfs_folder():
    global GFS_FOLDER
    for f in sorted(os.listdir(GFS_FOLDER), reverse=True):
        slug = f
        path = os.path.join(GFS_FOLDER, slug)
        if re.match(r'\d{10}', slug) and os.path.isdir(path) and len(glob(os.path.join(path, '*pwat.grib'))) > 0:
            return path, slug


def get_forecast_info():
    forecast_info = []
    for f in sorted(os.listdir(GFS_FOLDER), reverse=True):
        slug = f
        path = os.path.join(GFS_FOLDER, slug)
        if re.match(r'\d{10}', slug) and os.path.isdir(path) and len(glob(os.path.join(path, '*pwat.grib'))) > 0:
            slug_date = datetime.strptime(slug, "%Y%m%d%H")
            slug_date = slug_date.replace(tzinfo=pytz.UTC)
            forecast = {
                         "slug": slug,
                         "date": slug_date,
                        }
            if slug_date > datetime.now(pytz.utc):
                forecast['future'] = True
                forecast_info.append(forecast)
            else:
                forecast['future'] = False
                forecast_info.append(forecast)
                break
    return forecast_info


def get_latest_rainbows_url():
    slug = get_forecast_info()[-1]['slug']
    return "/static/gfs/" + slug + "/" + slug + ".rainbows.json"


def get_latest_clouds_url():
    slug = get_forecast_info()[-1]['slug']
    return "/static/gfs/" + slug + "/" + slug + ".clouds.json"


def get_latest_rainbow_cities_url():
    slug = get_forecast_info()[-1]['slug']
    return "/static/gfs/" + slug + "/" + slug + ".rainbow_cities.json"

def get_latest_clouds_alpha_url():
    slug = get_forecast_info()[-1]['slug']
    return "/static/gfs/{}/GFS_half_degree.clouds_alpha.{}.pwat.png".format(slug, slug)


LATEST_GFS_FOLDER, LATEST_GFS_SLUG = get_latest_gfs_folder()


"""
APP SETTINGS
"""

# By default, DEBUG=False, except on Mac OS X (because that’s most likely a development machine)
# You can override this setting by creating a file called local_settings.py

DEBUG = False
if sys.platform == "darwin":
    DEBUG = True

try:
    from local_settings import *
except ImportError:
    pass
