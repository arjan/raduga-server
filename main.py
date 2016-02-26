# -*- coding: utf-8 -*-

import json
import os
import pymongo
import time
import datetime
import glob
import requests

# Dependencies: Flask + PIL or Pillow
from flask import request, jsonify, abort
from werkzeug import secure_filename

# Local imports
import settings
import geo
import hq
import utils

from app import app, cache, db
from data.cities import data as cities

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
@cache.cached(timeout=60)
def get_latest_rainbow_cities():
    list = sorted(glob.glob(settings.GFS_FOLDER + "/*/*rainbow_cities.json"))[::-1]
    result = []
    date = None
    for f in list:
        if os.stat(f).st_size > 2:
            result = json.loads(open(f).read())
            date = datetime.datetime(*time.strptime(os.path.basename(f).split(".")[0], '%Y%m%d%H')[0:6])
            break

    if date is not None:
        d = datetime.datetime.utcnow() - date
        if d.days > 0 or d.seconds > 1 * 3600:
            result = []
        date = date.isoformat()

    photos = [p for p in db.photos.find().sort('created', pymongo.DESCENDING).limit(1)]
    photo = len(photos) > 0 and map_photo(photos[0]) or None
    d = datetime.datetime.utcnow() - photo['created']
    if d.days > 0 or d.seconds > 4 * 3600:
        photo = None
    return jsonify(dict(cities=result[:20], date=date, last_photo=photo))

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


def map_photo(p):
    return dict(created=p['created'],
                filename=p['filename'],
                id=p['id'],
                variants=p['variants'],
                meta=p.get('meta', ''))


@app.route("/app/user/<string:user_id>/photo", methods=['POST'])
def photo_upload(user_id):
    user = db.users.find_one({'id': user_id})
    #if user is None:
    #    abort(403)
    file = request.files['file']
    if not file or not allowed_file(file.filename):
        abort(400)
    file_id = "%s_%s" % (user_id, int(time.time()))
    src_file = os.path.join(settings.UPLOAD_FOLDER, "%s_%s" % (file_id, secure_filename(file.filename)))
    file.save(src_file)
    variants = dict([(str(w), resize(src_file, w)) for w in (200, 400, 800)])

    meta = request.values.get('meta', '')
    mm = json.loads(meta)
    if 'lat' in mm:
        geo = 'http://maps.google.com/maps/api/geocode/json'
        params = {'sensor': 'false', 'latlng': '%.5f,%.5f' % (mm['lat'], mm['lng'])}
        r = requests.get(geo, params)
        c = json.loads(r.text)['results'][0]
        mm['geocode'] = c
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
    c = sorted(cities, key=lambda c: (c['lat']-lat)*(c['lat']-lat) + (c['lon']-lon)*(c['lon']-lon))
    c = [dict(x, id=utils.city_id(x), distance=geo.geo_distance(lat, lon, x['lat'], x['lon'])) for x in c[:int(request.args.get('limit', 5))]]
    c = [x for x in c if x['distance'] < 100]
    return jsonify(dict(cities=c))


hq.build()

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
