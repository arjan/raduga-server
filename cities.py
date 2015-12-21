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

from glob import glob
from PIL import Image

import settings
from geo import position_to_point
import utils

logger = utils.install_logger()

s = requests.Session()

def _push(message, channels):
    data = json.dumps({"channels": channels, "data": {"alert": message.encode('utf8')}})
    headers = {"X-Parse-Application-Id": settings.PARSE_APPLICATION_ID,
               "X-Parse-REST-API-Key": settings.PARSE_REST_API_KEY,
               "Content-Type": "application/json"}
    r = s.post('https://api.parse.com/1/push', data=data, headers=headers)
    logger.debug("Push result: {}".format(r.text))
    

def send_push(city):
    logger.debug(u'send push {}'.format(city['name_en']).encode('utf8'))
    messages = {"en": u"High chance on rainbows near {}",
                "ru": u"Высокая вероятность на радугу в районе {}"}
    for lang, message in messages.iteritems():
        pf = "-" + lang
        channels = [utils.city_id(city)+pf] + [utils.city_id(n)+pf for n in city['nearby']]
        logger.debug(u"Sending pushes for city: {} to channels: {}".format(city['name_'+lang], channels).encode('utf8'))
        _push(message.format(city['name_'+lang]), channels)


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

    rainbow_cities = []

    logger.debug("checking each city against rainbow analysis")

    for city in cities:
        # position_to_point allows to translate a geographic coordinate into a pixel value
        # for the image we produced from the gfs data
        point = position_to_point((city['lon'], city['lat']))
        # there are black pixels where we predict rainbows
        if access[point[0], point[1]] == 0:
            rainbow_cities.append(city)

    if len(rainbow_cities) > 0:
        names = u', '.join((city['name_en'] for city in rainbow_cities)).encode('utf8')
        logger.debug(u"Found rainbow cities: %s" % names)
        [send_push(c) for c in rainbow_cities]
        _push(u"Rainbow cities: %s" % names, ["debug"])

    else:
        logger.debug("no rainbow cities found")

    with codecs.open(rainbow_cities_json_path, 'w', 'utf8') as f:
        f.write(json.dumps(rainbow_cities, indent=4, ensure_ascii=False))


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
            if len(glob(os.path.join(path, '*rainbow_cities.json'))) > 0:
                logger.debug("encountered already processed rainbow-forecast %s, stop searching for rainbow-forecasts" % slug)
                break
            if len(glob(os.path.join(path, '*pwat.grib'))) > 0:
                logger.debug("encountered cityless rainbow-forecast %s, start processing" % slug)
                find_rainbow_cities(slug)
