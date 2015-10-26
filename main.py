# -*- coding: utf-8 -*-

# Python Standard Library 
from datetime import datetime

# Dependencies: Flask + PIL or Pillow
from flask import send_from_directory, redirect as redirect_flask, render_template, request, Response, jsonify

# Local imports
from data.cities import data as cities
import geo
import hq
from app import app
import settings


# Redirects should not be cached by the devices:
def redirect(uri):
    """
    http://arusahni.net/blog/2014/03/flask-nocache.html
    """
    response = redirect_flask(uri)
    response.headers['Last-Modified'] = datetime.now()
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


@app.route("/latest/rainbow_cities.json")
def latest_rainbow_cities():
    return redirect(settings.get_latest_rainbow_cities_url())


@app.route("/latest/rainbows.json")
def latest_rainbows():
    return redirect(settings.get_latest_rainbows_url())


@app.route("/latest/clouds.json")
def latest_clouds():
    return redirect(settings.get_latest_clouds_url())


@app.route("/app/closest-cities")
def get_closest_cities():
    lat, lon = float(request.args.get('lat', 0)), float(request.args.get('lon', 0))
    if lat == 0 or lon == 0:
        raise RuntimeError("Invalid request")
    c = sorted(cities, key=lambda c: (c['lat']-lat)*(c['lat']-lat) + (c['lon']-lon)*(c['lon']-lon))
    c = [dict(x, distance=geo.geo_distance(lat, lon, x['lat'], x['lon'])) for x in c[:int(request.args.get('limit', 5))]]
    return jsonify(dict(cities=c))


hq.build()


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
