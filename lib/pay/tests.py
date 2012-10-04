# -*- coding: utf8 -*-
import os

from django import test
from django.conf import settings
from django.core.urlresolvers import reverse

from gelato.constants import base
import mock
from nose.tools import eq_
from samples import JWTtester

from lib.pay.forms import VerifyForm
from lib.pay.models import Addon, InappConfig

sample = os.path.join(os.path.dirname(__file__), 'sample.key')


class Base(JWTtester, test.TestCase):

    def setUp(self):
        super(Base, self).setUp()
        self.url = '/en-US' + reverse('verify')
        self.key = 'public.key'
        self.secret = 'private.secret'
        self.create()

    def create(self, key=None, secret=None):
        key = key or self.key
        secret = secret or self.secret
        self.app = Addon.objects.create(status=base.STATUS_PUBLIC)
        self.inapp = InappConfig.objects.create(addon=self.app, public_key=key)
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            self.inapp.set_private_key(secret)


@mock.patch.object(settings, 'KEY', 'marketplace.mozilla.org')
@mock.patch.object(settings, 'SECRET', 'marketplace.secret')
@mock.patch.object(settings, 'ISSUER', 'marketplace.mozilla.org')
@mock.patch.object(settings, 'INAPP_KEY_PATHS', {None: sample})
@mock.patch.object(settings, 'DEBUG', True)
class TestVerify(Base):

    def get(self, payload):
        return self.client.get('%s?req=%s' % (self.url, payload))

    def test_post(self):
        eq_(self.client.post(self.url).status_code, 405)

    def test_get(self):
        eq_(self.client.get(self.url).status_code, 400)

    def test_inapp(self):
        payload = self.request(iss=self.key, app_secret=self.secret)
        eq_(self.get(payload).status_code, 200)

    def test_inapp_wrong_secret(self):
        payload = self.request(iss=self.key, app_secret=self.secret + '.nope')
        eq_(self.get(payload).status_code, 400)

    def test_inapp_wrong_key(self):
        payload = self.request(iss=self.key + '.nope', app_secret=self.secret)
        eq_(self.get(payload).status_code, 400)

    def test_bad_payload(self):
        eq_(self.get('foo').status_code, 400)

    def test_unicode_payload(self):
        eq_(self.get(u'Հ').status_code, 400)

    def test_purchase(self):
        payload = self.request(iss=settings.KEY, app_secret=settings.SECRET)
        eq_(self.get(payload).status_code, 200)

    def test_debug(self):
        with self.settings(VERBOSE_LOGGING=True):
            payload = self.request(app_secret=self.secret + '.nope')
            res = self.get(payload)
            eq_(res.status_code, 400)
            assert res.content
            # TODO: assert it shows a big error message.

    def test_not_debug(self):
        with self.settings(VERBOSE_LOGGING=False):
            payload = self.request(app_secret=self.secret + '.nope')
            res = self.get(payload)
            eq_(res.status_code, 400)
            assert res.content
            # TODO: assert it does not show a big error message.


@mock.patch.object(settings, 'KEY', 'marketplace.mozilla.org')
@mock.patch.object(settings, 'SECRET', 'marketplace.secret')
class TestForm(Base):

    def failed(self, form):
        assert not form.is_valid()
        assert 'req' in form.errors

    def test_required(self):
        self.failed(VerifyForm({}))

    def test_empty(self):
        self.failed(VerifyForm({'req': ''}))

    def test_broken(self):
        self.failed(VerifyForm({'req': 'foo'}))

    def test_unicode(self):
        self.failed(VerifyForm({'req': u'Հ'}))

    def test_non_existant(self):
        payload = self.request(iss=self.key + '.nope', app_secret=self.secret)
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            form = VerifyForm({'req': payload})
            assert not form.is_valid()

    def test_not_public(self):
        self.app.status = base.STATUS_PENDING
        self.app.save()

        payload = self.request(iss=self.key, app_secret=self.secret)
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            form = VerifyForm({'req': payload})
            assert not form.is_valid()

    def test_valid_inapp(self):
        payload = self.request(iss=self.key, app_secret=self.secret)
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            form = VerifyForm({'req': payload})
            assert form.is_valid()
            # This means we've successfully looked up the InappConfig.
            eq_(form.key, self.key)
            eq_(form.secret, self.secret)

    def test_valid_purchase(self):
        payload = self.request(iss=settings.KEY, app_secret=settings.SECRET)
        form = VerifyForm({'req': payload})
        assert form.is_valid()
        eq_(form.key, settings.KEY)
        eq_(form.secret, settings.SECRET)
