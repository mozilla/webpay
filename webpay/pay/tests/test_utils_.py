from django.test.utils import override_settings

from nose.tools import raises

from webpay.base.tests import TestCase
from webpay.pay.utils import verify_urls


@override_settings(ALLOWED_CALLBACK_SCHEMES=['http', 'https'])
class TestVerifyURLs(TestCase):

    @raises(ValueError)
    def test_bad(self):
        verify_urls('foo')

    def test_good(self):
        verify_urls('http://foo.com')

    @raises(ValueError)
    def test_ftp(self):
        verify_urls('ftp://foo.com')

    @raises(ValueError)
    def test_https_only(self):
        with self.settings(ALLOWED_CALLBACK_SCHEMES=['https']):
            verify_urls('http://foo.com')
