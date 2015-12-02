import os
import json
import main
import unittest
import tempfile
from StringIO import StringIO

import logging
logging.basicConfig(level=logging.WARNING)


class APITestCase(unittest.TestCase):

    def setUp(self):
        self.app = main.app.test_client()

    def test_user(self):
        rv = self.app.get('/notfound')
        assert rv.status_code == 404

        # register user
        rv = self.app.post('/app/user/test1', data=json.dumps(dict(email='foo')), headers={'content-type': 'application/json'})
        assert rv.status_code == 200

        # upload photo
        rv = self.app.post('/app/user/nonexistinguser-test1/photo', data = {'file': (StringIO('my file contents'), 'hello world.png')})
        assert rv.status_code == 403

        # upload photo
        fp = open(os.path.join(os.path.dirname(__file__), "test.png"), "r")
        rv = self.app.post('/app/user/test1/photo', data={'meta': 'testvalue xxx', 'file': (fp, 'test.png')})
        assert rv.status_code == 200
        
        # get photos
        rv = self.app.get('/app/user/test1/photos')
        photos = json.loads(rv.data)
        assert len(photos['photos']) > 1

        # get photos
        rv = self.app.get('/app/photos')
        photos = json.loads(rv.data)
        assert len(photos['photos']) > 1

        

if __name__ == '__main__':
    unittest.main()
