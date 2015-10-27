# -*- coding: utf-8 -*-

import json
import os
import re

# Dependencies: Flask + PIL or Pillow
from flask import request, jsonify

# Local imports
import settings
import geo
import hq
import utils

from app import app, cache, db
from data.cities import data as cities


@app.route("/latest/rainbow_cities.json")
def latest_rainbow_cities():
    return utils.nocache_redirect(settings.get_latest_rainbow_cities_url())


@app.route("/latest/rainbows.json")
def latest_rainbows():
    return utils.nocache_redirect(settings.get_latest_rainbows_url())


@app.route("/latest/clouds.json")
def latest_clouds():
    return utils.nocache_redirect(settings.get_latest_clouds_url())


@app.route("/app/rainbow-cities")
@cache.cached(timeout=60)
def get_rainbow_cities():
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), settings.get_latest_rainbow_cities_url()[1:]))
    return jsonify(dict(cities=json.loads(open(path).read())))


@app.route("/app/user/<string:id>", methods=['POST'])
def register_user(id):
    user_data = dict(request.get_json(), id=id)
    db.users.update({'id': id}, user_data, True)
    return jsonify(dict(result="ok"))


@app.route("/latest/clouds.png")
@cache.cached(timeout=60)
def get_clouds_png():
    return utils.nocache_redirect(settings.get_latest_clouds_alpha_url())


@app.route("/app/closest-cities")
def get_closest_cities():
    lat, lon = float(request.args.get('lat', 0)), float(request.args.get('lon', 0))
    if lat == 0 or lon == 0:
        raise RuntimeError("Invalid request")
    c = sorted(cities, key=lambda c: (c['lat']-lat)*(c['lat']-lat) + (c['lon']-lon)*(c['lon']-lon))
    c = [dict(x, id=utils.city_id(x), distance=geo.geo_distance(lat, lon, x['lat'], x['lon'])) for x in c[:int(request.args.get('limit', 5))]]
    c = [x for x in c if x['distance'] < 100]
    return jsonify(dict(cities=c))


hq.build()

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
