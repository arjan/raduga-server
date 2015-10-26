# -*- coding: utf-8 -*-

# Dependencies: Flask + PIL or Pillow
from flask import Flask
import pymongo

app = Flask(__name__)

db = pymongo.MongoClient().raduga
