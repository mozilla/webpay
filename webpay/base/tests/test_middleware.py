from django import http
from django.conf import settings
from django.test import TestCase
from django.test.client import RequestFactory

import fudge
from nose.tools import eq_

from webpay.base.middleware import LocaleMiddleware


class TestLocaleMiddleware(TestCase):

    def process(self, **request_kw):
        loc = LocaleMiddleware()
        req = RequestFactory().get('/', **request_kw)
        loc.process_request(req)
        resp = http.HttpResponse('output')
        loc.process_response(req, resp)
        return req.locale, resp

    def test_accept_exact(self):
        with self.settings(LANGUAGE_CODE='ja'):
            eq_(self.process(HTTP_ACCEPT_LANGUAGE='en-us')[0], 'en-US')

    @fudge.patch('tower.activate')
    def test_activate_tower(self, fake_activate):
        fake_activate.expects_call()
        self.process(HTTP_ACCEPT_LANGUAGE='en-us')

    def test_accept_prefix(self):
        with self.settings(LANGUAGE_CODE='ja'):
            eq_(self.process(HTTP_ACCEPT_LANGUAGE='en')[0], 'en-US')

    def test_accept_first_prefix_wins(self):
        # See bug 439568.
        eq_(self.process(HTTP_ACCEPT_LANGUAGE='en,ja;q=0.9,fr;q=0.8,de;'
                                              'q=0.7,es;q=0.6,it;q=0.5,nl;'
                                              'q=0.4,sv;q=0.3,nb;q=0.2')[0],
            'en-US')

    def test_accept_not_supported(self):
        eq_(self.process(HTTP_ACCEPT_LANGUAGE='foo')[0],
            settings.LANGUAGE_CODE)

    def test_accept_varies_cache(self):
        locale, resp = self.process(HTTP_ACCEPT_LANGUAGE='en-us')
        eq_(resp['Vary'], 'Accept-Language')

    def test_default_to_lang_code(self):
        with self.settings(LANGUAGE_CODE='de'):
            eq_(self.process(HTTP_ACCEPT_LANGUAGE='foo')[0], 'de')

    def test_lang_exact(self):
        with self.settings(LANGUAGE_CODE='ja'):
            eq_(self.process(data=dict(lang='en-us'))[0], 'en-US')

    def test_lang_wrong_suffix(self):
        with self.settings(LANGUAGE_CODE='ja'):
            eq_(self.process(data=dict(lang='en-xx'))[0], 'en-US')

    def test_lang_prefix(self):
        with self.settings(LANGUAGE_CODE='ja'):
            eq_(self.process(data=dict(lang='en'))[0], 'en-US')

    def test_lang_non_existant(self):
        eq_(self.process(data=dict(lang='xx'))[0], settings.LANGUAGE_CODE)

    def test_no_input(self):
        eq_(self.process()[0], settings.LANGUAGE_CODE)
