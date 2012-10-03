import json

from django import test
from django.conf import settings
from django.core.urlresolvers import reverse

import jwt
import mock
from nose.tools import eq_
from samples import JWTtester


@mock.patch.object(settings, 'KEY', JWTtester.key)
@mock.patch.object(settings, 'SECRET', JWTtester.secret)
class TestVerify(JWTtester, test.TestCase):

    def setUp(self):
        super(TestVerify, self).setUp()
        self.url = '/en-US' + reverse('verify')

    def get(self, payload):
        return self.client.get('%s?req=%s' % (self.url, payload))

    def test_post(self):
        eq_(self.client.post(self.url).status_code, 405)

    def test_get(self):
        eq_(self.client.get(self.url).status_code, 400)

    def test_get_some_jwt(self):
        payload = self.request(app_secret=self.secret)
        eq_(self.get(payload).status_code, 200)

    def test_debug(self):
        with self.settings(DEBUG=True):
            payload = self.request(app_secret='foo')
            res = self.get(payload)
            eq_(res.status_code, 400)
            assert res.content

    def test_not_debug(self):
        with self.settings(DEBUG=False):
            payload = self.request(app_secret='foo')
            res = self.get(payload)
            eq_(res.status_code, 400)
            assert res.content
