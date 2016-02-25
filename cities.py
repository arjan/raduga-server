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
    data = json.dumps({"channels": channels, "data": {"alert": message}})
    headers = {"X-Parse-Application-Id": settings.PARSE_APPLICATION_ID,
               "X-Parse-REST-API-Key": settings.PARSE_REST_API_KEY,
               "Content-Type": "application/json"}
    r = s.post('https://api.parse.com/1/push', data=data, headers=headers)
    logger.debug("Push result: {}".format(r.text.strip()))


def send_push(city):
    messages = {"en": u"High chance on rainbows near {}"}
    if city['country'] == 'ru':
        messages["ru"] = u"Высокая вероятность на радугу в районе {}"
    for lang, message in messages.items():
        if lang != 'en':
            name = city['name']
        else:
            name = city['name_en']
        pf = "-" + lang
        channels = [utils.city_id(city)+pf] #+ [utils.city_id(n)+pf for n in city['nearby']]
        logger.debug(u"Sending pushes for city: {} ({})".format(name, lang).encode('utf8'))
        _push(message.format(name), channels)


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

    cur = psql.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM worldcities WHERE xy IN (" + (",".join(xys)) + ")")
    rainbow_cities = cur.fetchall()

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
    city = {"href_en": "http://en.wikipedia.org/wiki/Ust-Labinsk", "name_ru": u"Усть-Лабинск", "name_en": u"Ust-Labinsk", "nearby": ["Adygeysk", "Apsheronsk", "Belorechensk", "Goryachy Klyuch", "Gulkevichi", "Khadyzhensk", "Korenovsk", "Krasnodar", "Kropotkin", "Kurganinsk", "Maykop", "Tikhoretsk", "Timashyovsk"], "lon": 39.7, "lat": 45.217}
    _push(u"Test push message", ["debug"])
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
            find_rainbow_cities(slug)
            if len(glob(os.path.join(path, 'PROCESSED'))) > 0:
                logger.debug("encountered already processed folder %s, stop searching for rainbow-forecasts" % slug)
                break
            if len(glob(os.path.join(path, '*pwat.grib'))) > 0:
                logger.debug("encountered cityless rainbow-forecast %s, start processing" % slug)
                find_rainbow_cities(slug)
