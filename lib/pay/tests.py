import json

from django import test
from django.core.urlresolvers import reverse

import jwt
from nose.tools import eq_

from moz_inapp_pay.tests import JWTtester

class TestVerify(JWTtester):

    def setUp(self):
        self.url = '/en-US' + reverse('verify')

    def test_get(self):
        eq_(self.client.get(self.url).status_code, 405)

    def test_post_bad(self):
        eq_(self.client.post(self.url).status_code, 400)

    def test_post_some_jwt(self):
        payload = self.request()
        eq_(self.client.post(self.url, payload).status_code, 200)
