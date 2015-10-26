# -*- coding: utf-8 -*-

# Dependencies: Flask + PIL or Pillow
from flask import Flask
from flask.ext.cache import Cache
import pymongo

app = Flask(__name__)

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

db = pymongo.MongoClient().raduga
