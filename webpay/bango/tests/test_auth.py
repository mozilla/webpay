import base64

from django.test import TestCase

from nose.tools import ok_
from test_utils import RequestFactory

from webpay.bango.auth import basic


class TestAuth(TestCase):
    key = 'HTTP_AUTHORIZATION'

    def test_no_header(self):
        ok_(not basic(RequestFactory().get('/')))

    def test_malformed(self):
        rf = RequestFactory().get('/', **{self.key: ' '})
        ok_(not basic(rf))

    def test_not_basic(self):
        rf = RequestFactory().get('/', **{self.key: 'Not-basic something'})
        ok_(not basic(rf))

    def test_not_base64(self):
        rf = RequestFactory().get('/', **{self.key: 'basic something'})
        ok_(not basic(rf))

    def test_wrong_username(self):
        with self.settings(BANGO_BASIC_AUTH={'user': 'u', 'password': 'p'}):
            encoded = base64.encodestring('user:pass')
            rf = RequestFactory().get('/', **{self.key: 'basic ' + encoded})
            ok_(not basic(rf))

    def test_right_username(self):
        with self.settings(BANGO_BASIC_AUTH={'user': 'u', 'password': 'p'}):
            encoded = base64.b64encode('u:p')
            rf = RequestFactory().get('/', **{self.key: 'basic ' + encoded})
            ok_(basic(rf))
