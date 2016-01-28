import os
import json
from functools import wraps
from flask import Flask, send_from_directory, redirect, render_template, request, Response, jsonify
import pymongo

# Local imports
import settings
from app import app, db


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == 'admin' and password == settings.HQ_PASSWORD


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response('Please log in first', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


def build():

    @app.route('/')
    def index():
        return redirect('/hq/')

    @app.route("/hq/gfs/<string:slug>")
    @requires_auth
    def hq_slug(slug):
        return render_template("hq_slug.html", slug=slug)

    @app.route("/hq/")
    @requires_auth
    def hq():
        logs = db.log.find(limit=500).sort("$natural", pymongo.DESCENDING)
        forecasts = settings.get_forecast_info()
        gfs = sorted(os.listdir(settings.GFS_FOLDER))
        return render_template("hq.html", logs=logs, forecasts=forecasts, gfs=gfs)

    @app.route("/hq/moderate")
    @requires_auth
    def moderate():
        reports = list(db.reports.find(limit=500).sort("$natural", pymongo.DESCENDING))
        photos = list(db.photos.find({'id': {'$in': [r['photo_id'] for r in reports]}}))
        lookup = dict([ (p['id'], p) for p in photos])
        for r in reports:
            photo = lookup.get(r['photo_id'], None)
            r['photo'] = photo
            try:
                r['city'] = json.loads(photo['meta'])['geocode']['formatted_address']
            except Exception as e:
                print(e)
                r['city'] = 'Unknown'
        return render_template("moderate.html", reports=reports)
