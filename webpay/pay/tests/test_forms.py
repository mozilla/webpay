# -*- coding: utf-8 -*-
import json

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

import mock
from nose import SkipTest
from nose.tools import eq_

from webpay.pay.forms import VerifyForm
from webpay.pay.models import ISSUER_INACTIVE

from . import Base, sample


@mock.patch.object(settings, 'KEY', 'marketplace.mozilla.org')
@mock.patch.object(settings, 'SECRET', 'marketplace.secret')
class TestForm(Base):

    def setUp(self):
        super(TestForm, self).setUp()
        p = mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
        p.start()
        self.addCleanup(p.stop)

    def failed(self, form):
        assert not form.is_valid()
        assert 'req' in form.errors

    def test_required(self):
        self.failed(VerifyForm({}))

    def test_empty(self):
        self.failed(VerifyForm({'req': ''}))

    def test_broken(self):
        self.failed(VerifyForm({'req': 'foo'}))

    def test_debug(self):
        with self.settings(VERBOSE_LOGGING=True):
            payload = self.request(app_secret=self.secret + '.nope')
            res = self.get(payload)
            eq_(res.status_code, 400)
            # Output should show exception message.
            self.assertContains(res,
                                'InvalidJWT: Signature verification failed',
                                status_code=400)

    def test_not_debug(self):
        with self.settings(VERBOSE_LOGGING=False):
            payload = self.request(app_secret=self.secret + '.nope')
            res = self.get(payload)
            eq_(res.status_code, 400)
            # Output should show a generic error message without details.
            self.assertContains(res, 'There was an error', status_code=400)


@mock.patch.object(settings, 'KEY', 'marketplace.mozilla.org')
@mock.patch.object(settings, 'SECRET', 'marketplace.secret')
class TestVerifyForm(Base):

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

    @mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
    def test_non_existant(self, get_active_product):
        get_active_product.side_effect = ObjectDoesNotExist
        payload = self.request(iss=self.key + '.nope', app_secret=self.secret)
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            form = VerifyForm({'req': payload})
            assert not form.is_valid()

    def test_not_public(self):
        # Should this be moved down to solitude? There currently isn't
        # an active status in solitude.
        raise SkipTest

        self.iss.status = ISSUER_INACTIVE
        self.iss.save()
        payload = self.request(iss=self.key, app_secret=self.secret)
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            form = VerifyForm({'req': payload})
            assert not form.is_valid()

    @mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
    def test_valid_inapp(self, get_active_product):
        self.set_secret(get_active_product)
        payload = self.request(iss=self.key, app_secret=self.secret)
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            form = VerifyForm({'req': payload})
            assert form.is_valid()
            # This means we've successfully looked up the InappConfig.
            eq_(form.key, self.key)
            eq_(form.secret, self.secret)

    def test_double_encoded_jwt(self):
        payload = self.payload()
        # Some jwt libraries are doing this, I think.
        payload = json.dumps(payload)
        req = self.request(iss=self.key, app_secret=self.secret,
                           payload=payload)
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            form = VerifyForm({'req': req})
            assert not form.is_valid()

    def test_valid_purchase(self):
        payload = self.request(iss=settings.KEY, app_secret=settings.SECRET)
        form = VerifyForm({'req': payload})
        assert form.is_valid()
        eq_(form.key, settings.KEY)
        eq_(form.secret, settings.SECRET)
