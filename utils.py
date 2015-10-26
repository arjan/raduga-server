# -*- coding: utf-8 -*-
"""
Utilities.

For now: a logger.

The logger has two possible behaviours, based on the DEBUG setting.

If DEBUG is true, the logger prints to stdout.
See: http://stackoverflow.com/questions/2302315/how-can-info-and-debug-logging-message-be-sent-to-stdout-and-higher-level-messag#answer-9323805

If DEBUG is false, the logger logs to a MongoDB database.
In this way, it is easy to keep all the logs in one place,
and show them in a web-based monitoring application.

The code for the MongoDB logger is taken from https://github.com/puentesarrin/mongodb-log
See LICENSE info below.
"""

import flask

import sys
import logging
import getpass

from bson import InvalidDocument
from datetime import datetime
from pymongo.collection import Collection
from socket import gethostname

from settings import DEBUG

try:
    from pymongo import MongoClient as Connection
except ImportError:
    from pymongo import Connection

if sys.version_info[0] >= 3:
    unicode = str


class MongoFormatter(logging.Formatter):
    def format(self, record):
        """Format exception object as a string"""
        data = record.__dict__.copy()

        if record.args:
            msg = record.msg % record.args
        else:
            msg = record.msg

        data.update(
            username=getpass.getuser(),
            time=datetime.now(),
            host=gethostname(),
            message=msg,
            args=tuple(unicode(arg) for arg in record.args)
        )
        if 'exc_info' in data and data['exc_info']:
            data['exc_info'] = self.formatException(data['exc_info'])
        return data


class MongoHandler(logging.Handler):
    """ Custom log handler

    Logs all messages to a mongo collection. This  handler is
    designed to be used with the standard python logging mechanism.
    """

    @classmethod
    def to(cls, collection, db='mongolog', host='localhost', port=None,
        username=None, password=None, level=logging.NOTSET):
        """ Create a handler for a given  """
        return cls(collection, db, host, port, username, password, level)

    def __init__(self, collection, db='mongolog', host='localhost', port=None,
        username=None, password=None, level=logging.NOTSET):
        """ Init log handler and store the collection handle """
        logging.Handler.__init__(self, level)
        if isinstance(collection, str):
            connection = Connection(host, port)
            if username and password:
                connection[db].authenticate(username, password)
            self.collection = connection[db][collection]
        elif isinstance(collection, Collection):
            self.collection = collection
        else:
            raise TypeError('collection must be an instance of basestring or '
                             'Collection')
        self.formatter = MongoFormatter()

    def emit(self, record):
        """ Store the record to the collection. Async insert """
        try:
            self.collection.insert(self.format(record))
        except InvalidDocument as e:
            logging.error("Unable to save log record: %s", e.message,
                exc_info=True)


def install_logger():
    logger = logging.getLogger('Радуга')
    logger.setLevel(logging.DEBUG)

    if DEBUG:
        ch = logging.StreamHandler(sys.__stdout__)
        ch.setLevel(logging.DEBUG)
    
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
    
        logger.addHandler(ch)
    else:
        logger.addHandler(MongoHandler.to(db='raduga', collection='log'))

    return logger


# Redirects should not be cached by the devices:
def nocache_redirect(uri):
    """
    http://arusahni.net/blog/2014/03/flask-nocache.html
    """
    response = flask.redirect(uri)
    response.headers['Last-Modified'] = datetime.now()
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response
