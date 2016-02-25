# -*- coding: utf-8 -*-

# Dependencies: Flask + PIL or Pillow
from flask import Flask
from flask.ext.cache import Cache
from flask.ext.cors import CORS

from local_settings import POSTGRES
import pymongo
import psycopg2

app = Flask(__name__)

# app.logger.setLevel(logging.DEBUG)

cors = CORS(app)

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

db = pymongo.MongoClient().raduga

psql = psycopg2.connect(POSTGRES)
