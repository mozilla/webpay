import base64

from django.test import TestCase

from nose.tools import raises
from test_utils import RequestFactory

from webpay.bango.auth import basic


class TestAuth(TestCase):
    key = 'HTTP_AUTHORIZATION'

    @raises(ValueError)
    def test_no_header(self):
        basic(RequestFactory().get('/'))

    @raises(ValueError)
    def test_malformed(self):
        basic(RequestFactory().get('/', **{self.key: ' '}))

    @raises(ValueError)
    def test_not_basic(self):
        basic(RequestFactory().get('/', **{self.key: 'Not-basic something'}))

    @raises(ValueError)
    def test_not_base64(self):
        basic(RequestFactory().get('/', **{self.key: 'basic something'}))

    @raises(ValueError)
    def test_no_split(self):
        encoded = base64.encodestring('user')
        basic(RequestFactory().get('/', **{self.key: encoded}))
