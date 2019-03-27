# -*- coding: utf-8 -*-

import json
import os
import pymongo
import time
import datetime
import glob
import requests
import psycopg2.extras
import base64

# Dependencies: Flask + PIL or Pillow
from flask import request, jsonify, abort
from werkzeug import secure_filename

# Local imports
import settings
import hq
import utils

from app import app, cache, db, psql

logger = utils.install_logger()


@app.route("/latest/rainbow_cities.json")
def latest_rainbow_cities():
    return utils.nocache_redirect(settings.get_latest_rainbow_cities_url())


@app.route("/latest/rainbows.json")
def latest_rainbows():
    return utils.nocache_redirect(settings.get_latest_rainbows_url())


@app.route("/latest/clouds.json")
def latest_clouds():
    return utils.nocache_redirect(settings.get_latest_clouds_url())


@app.route("/app/old-rainbow-cities")
@cache.cached(timeout=60)
def get_rainbow_cities():
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), settings.get_latest_rainbow_cities_url()[1:]))
    return jsonify(dict(cities=json.loads(open(path).read())))

@app.route("/app/rainbow-cities")
def get_latest_rainbow_cities():
    result = []
    if os.path.exists(settings.GFS_FOLDER + "/rainbow_cities.json"):
        result = json.loads(open(settings.GFS_FOLDER + "/rainbow_cities.json", "r").read())

    photos = [p for p in db.photos.find().sort('created', pymongo.DESCENDING).limit(1)]
    photo = len(photos) > 0 and map_photo(photos[0]) or None
    if photo:
        d = datetime.datetime.utcnow() - photo['created']
        if d.days > 0 or d.seconds > 4 * 3600:
            photo = None
    return jsonify(dict(cities=result[:20], last_photo=photo))

@app.route("/app/tmp")
def tmp():
    list = sorted(glob.glob(settings.GFS_FOLDER + "/*/*rainbow_cities.json"))[::-1]
    return jsonify(result=list)

@app.route("/app/user/<string:id>", methods=['POST'])
def register_user(id):
    user_data = dict(request.get_json(), id=id)
    db.users.update({'id': id}, user_data, True)
    return jsonify(dict(result="ok"))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ['jpg', 'png', 'jpeg']

def resize(src_file, width):
    base, ext = os.path.basename(src_file).split(".", 2)
    target_file = os.path.join(os.path.dirname(src_file), "%s_%dw.%s" % (base, width, ext))
    cmd = "convert '%s' -auto-orient -resize %dx '%s'" % (src_file, width, target_file)
    os.system(cmd)
    return os.path.basename(target_file)


def closest_cities(lat, lon):
    q = "SELECT * FROM worldcities WHERE (point(%(lon)s, %(lat)s) <@> POINT(longitude, latitude)) / 1.60934 < 100 ORDER BY (point(%(lon)s, %(lat)s) <@> POINT(longitude, latitude)) ASC LIMIT 5"
    cur = psql.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(q, {'lat': lat, 'lon': lon})
    c = cur.fetchall()
    return [dict(city, id=utils.city_id(city)) for city in c]

def map_photo(p):
    return dict(created=p['created'],
                filename=p['filename'],
                id=p['id'],
                variants=p['variants'],
                meta=p.get('meta', ''))


@app.route("/app/user/<string:user_id>/photo", methods=['POST'])
def photo_upload(user_id):
    user = db.users.find_one({'id': user_id})

    blocked = db.blocked_users.find_one({'user_id': user_id}) is not None
    if blocked:
        abort(403)

    body = request.get_json()
    if body['photo']:
        (header, data) = body['photo'].split(",", 1)
        file_id = "%s_%s" % (user_id, int(time.time()))
        src_file = os.path.join(settings.UPLOAD_FOLDER, "%s.jpg" % (file_id))
        print(src_file)
        fp = open(src_file, 'wb')
        fp.write(base64.b64decode(data.encode('utf-8')))
        fp.close()
    else:
        print("bad request")
        abort(400)

    variants = dict([(str(w), resize(src_file, w)) for w in (200, 400, 800)])

    mm = 'meta' in body and body['meta'] or {}
    if 'lat' in mm:
        print(mm)
        c = closest_cities(mm['lat'], mm['lng'])
        if len(c) > 0:
            mm.update(c[0])
    meta = json.dumps(mm)

    doc = dict(id=file_id,
               filename=os.path.basename(src_file),
               user_id=user_id,
               meta=meta,
               created=datetime.datetime.utcnow(),
               variants=variants)
    logger.debug("Photo upload: {}".format(doc))
    db.photos.insert(doc)
    return jsonify(map_photo(doc))


@app.route("/app/user/<string:user_id>/photos", methods=['GET'])
def user_photos(user_id):
    limit = int(request.args.get('limit', 20))
    skip = int(request.args.get('skip', 0))
    user = db.users.find_one({'id': user_id})
    if user is None:
        abort(403)
    photos = db.photos.find({'user_id': user_id}).sort('created', pymongo.DESCENDING).limit(limit).skip(skip)
    return jsonify(dict(photos=[map_photo(p) for p in photos]))


@app.route("/app/photos", methods=['GET'])
def all_photos():
    limit = int(request.args.get('limit', 20))
    skip = int(request.args.get('skip', 0))
    photos = db.photos.find().sort('created', pymongo.DESCENDING).limit(limit).skip(skip)
    return jsonify(dict(photos=[map_photo(p) for p in photos]))


@app.route("/latest/clouds.png")
@cache.cached(timeout=60)
def get_clouds_png():
    return utils.nocache_redirect(settings.get_latest_clouds_alpha_url())

@app.route("/app/report/<string:photo_id>", methods=['POST'])
def report_photo(photo_id):
    reason = request.get_json().get('reason', "")
    db.reports.insert(dict(photo_id=photo_id, reason=reason, created=datetime.datetime.utcnow()))
    logger.debug("Photo reported: {} / {}".format(photo_id, reason))
    return jsonify(dict(result="ok"))

@app.route("/app/closest-cities")
def get_closest_cities():
    lat, lon = float(request.args.get('lat', 0)), float(request.args.get('lon', 0))
    if lat == 0 or lon == 0:
        raise RuntimeError("Invalid request")
    return jsonify(dict(cities=closest_cities(lat, lon)))


hq.build()

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
