# -*- coding: utf-8 -*-
"""
Load a list of Russian cities with their coordinates

Open the latest predicted rainbows image as created by water.py
Check which cities are in one of the rainbow areas.

Create a file "YYYYMMDDHH.rainbow_cities.json" that can be served
to the application.
"""

import re
import os
import sys
import json
import codecs
import requests
import psycopg2.extras

from glob import glob
from PIL import Image

import settings
from geo import position_to_point
import utils
from app import psql

logger = utils.install_logger()

s = requests.Session()

def _push(message, channels):
    for channel in channels:
        data = json.dumps({"to": channel, "data": {"message": message}})
        headers = {"Content-Type": "application/json"}
        r = s.post('https://api.pushy.me/push?api_key=' + settings.PUSHY_KEY, data=data, headers=headers)
        logger.debug("PUSH TO {} → result: {}".format(channel, r.text.strip()))


def send_push(city):
    template = u"High chance on rainbows near {}"
    if city['country'] == 'ru':
        template = u"Радуга обнаружена на расстоянии {}"
    if city['country'] == 'cn':
        template = u"发现彩虹：距你 {}"
    channels = ['/topics/city-' + utils.city_id(city)]
    name = city['name']
    logger.debug(u"Sending pushes for city: {} ({})".format(name, str(channels)).encode('utf8'))
    _push(template.format(name), channels)


def find_rainbow_cities(GFS_SLUG):
    logger.debug("loading list of cities")
    cities = json.loads(open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "data", "cities.json")).read())

    logger.debug("loading specified rainbow analysis image")
    CURRENT_GFS_FOLDER = os.path.join(settings.GFS_FOLDER, GFS_SLUG)
    rainbow_analysis_image_path = os.path.join(CURRENT_GFS_FOLDER, "GFS_half_degree.%s.pwat.png" % GFS_SLUG)
    try:
        image = Image.open(rainbow_analysis_image_path)
    except IOError:
        logger.error("did not find image file")
        return False

    access = image.load()

    rainbow_cities_json_path = os.path.join(CURRENT_GFS_FOLDER, "%s.rainbow_cities.json" % GFS_SLUG)
    processed_path = os.path.join(CURRENT_GFS_FOLDER, "PROCESSED")

    rainbow_cities = []

    logger.debug("checking each city against rainbow analysis")

    xys = []
    for x in range(image.size[0]):
        for y in range(image.size[1]):
            if access[x, y] == 0:
                xys.append("'%dx%d'" % (x, y))
    if len(xys) > 0:
        cur = psql.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM worldcities WHERE xy IN (" + (",".join(xys)) + ")")
        rainbow_cities = cur.fetchall()
    else:
        rainbow_cities = []

    if len(rainbow_cities) > 0:
        names = u', '.join((city['name_en'] for city in rainbow_cities)).encode('utf8')
        logger.debug(u"Found rainbow cities: %s" % names)
        [send_push(c) for c in rainbow_cities]
        _push(u"Rainbow cities: %s" % names, ["debug"])

        logger.debug(u"Wrote: %s" % rainbow_cities_json_path)
        files = [os.path.join(settings.GFS_FOLDER, "rainbow_cities.json"), rainbow_cities_json_path]
        for fn in files:
            with codecs.open(fn, 'w', 'utf8') as f:
                f.write(json.dumps(rainbow_cities, indent=4, ensure_ascii=False))
            logger.debug(u"Wrote {}".format(fn))

    else:
        logger.debug("no rainbow cities found")

    with codecs.open(processed_path, 'w', 'utf8') as f:
        f.write('processed')



def test_notifications():
    city = {'id': 'f4be2e51ef2a9c01007d0025280664b2', 'country': 'cn', 'name': 'Dawukou', 'name_en': 'Dawukou'}
    _push(u"Test push message", ["/topics/debugging"])
    # _push(u"Test push message", ["/topics/city-amsterdam"])
    #send_push(city)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test-notifications':
        test_notifications()
        exit(0)

    logger.debug('looking for rainbow-forecasts for which to find cities')
    for f in sorted(os.listdir(settings.GFS_FOLDER), reverse=True):
        slug = f
        path = os.path.join(settings.GFS_FOLDER, slug)
        if re.match(r'\d{10}', slug) and os.path.isdir(path):
            #find_rainbow_cities(slug)
            if len(glob(os.path.join(path, 'PROCESSED'))) > 0:
                logger.debug("encountered already processed folder %s, stop searching for rainbow-forecasts" % slug)
                break
            if len(glob(os.path.join(path, '*pwat.grib'))) > 0:
                logger.debug("encountered cityless rainbow-forecast %s, start processing" % slug)
                find_rainbow_cities(slug)
