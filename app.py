# -*- coding: utf-8 -*-

# Dependencies: Flask + PIL or Pillow
from flask import Flask
from flask.ext.cache import Cache
from flask.ext.cors import CORS

import pymongo

app = Flask(__name__)

cors = CORS(app)

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

db = pymongo.MongoClient().raduga
