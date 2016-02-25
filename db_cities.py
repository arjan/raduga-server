import json
import utils
import csv
import hashlib

from app import psql
from psycopg2 import ProgrammingError

logger = utils.install_logger()


def position_to_point(position):
    lng = position[0]
    while lng < 0:
        lng += 360
    return (int(lng * 2), int((position[1] - 90) * -2))


def xy(lat, lng):
    return "%dx%d" % position_to_point((lng, lat))


def install_schema():
    logger.info("Installing database schema")
    cur = psql.cursor()
    cur.execute(open("scrape/worldcities.sql", 'r').read())
    psql.commit()


def city_id(lat, lng):
    return hashlib.md5(("%s:%s" % (lat, lng)).encode('utf-8')).hexdigest()


def save(city):
    cur = psql.cursor()
    cur.execute("INSERT INTO worldcities (id, country, latitude, longitude, xy, name, name_en) SELECT %(id)s, %(country)s, %(latitude)s, %(longitude)s, %(xy)s, %(name)s, %(name_en)s WHERE NOT EXISTS (SELECT 1 FROM worldcities WHERE id = %(id)s)", city)


def fill_db():
    with open('scrape/cities.txt', 'rU') as f:
        for row in f:
            row = row.split(",")
            (country, _unused, name, _code, pop, lat, lng) = row
            lat = float(lat)
            lng = float(lng)
            pop = int(pop)
            if pop < 50000:
                continue
            id = city_id(lat, lng)    
            city = {'id': id, 'latitude': lat, 'longitude': lng, 'xy': xy(lat, lng), 'name': name, 'name_en': name, 'country': country}
            save(city)
        psql.commit()

def fill_db_ru():
    cities = json.loads(open('data/cities.json', 'r').read())
    for c in cities:
        id = city_id(c['lat'], c['lon'])
        city = {'id': id, 'latitude': c['lat'], 'longitude': c['lon'], 'xy': xy(c['lat'], c['lon']), 'name': c['name_ru'], 'name_en': c['name_en'], 'country': 'ru'}
        save(city)
    psql.commit()


try:
    cur = psql.cursor()
    cur.execute("SELECT * FROM worldcities LIMIT 1")
except ProgrammingError:
    psql.rollback()
    install_schema()
finally:
    cur.close()

#fill_db()
fill_db_ru()    