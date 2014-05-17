# -*- coding: utf-8 -*-
import json

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

import mock
from nose import SkipTest
from nose.tools import eq_, ok_

from webpay.pay.forms import VerifyForm, NetCodeForm

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


class TestNetCodeForm(Base):

    def test_not_mcc(self):
        form = NetCodeForm({'mcc': 'fooo', 'mnc': '1'})
        form.is_valid()
        ok_('mcc' in form.errors, form.errors)
        ok_('mnc' in form.errors, form.errors)

    def test_mcc(self):
        form = NetCodeForm({'mcc': '123', 'mnc': '456'})
        form.is_valid()
        ok_('mcc' not in form.errors, form.errors)
        ok_('mnc' not in form.errors, form.errors)

    def test_no_data(self):
        form = NetCodeForm({'mcc': '', 'mnc': ''})
        eq_(form.is_valid(), False)


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

    def test_not_mcc(self):
        form = VerifyForm({'mcc': 'fooo', 'mnc': '1'})
        form.is_valid()
        assert 'mcc' in form.errors
        assert 'mnc' in form.errors

    def test_mcc(self):
        form = VerifyForm({'mcc': '123', 'mnc': '456'})
        form.is_valid()
        assert 'mcc' not in form.errors
        assert 'mnc' not in form.errors

    def test_only_mnc(self):
        form = VerifyForm({'mnc': '456'})
        form.is_valid()
        assert 'mcc' not in form.errors
        assert 'mnc' not in form.errors
        assert '__all__' in form.errors

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

    def test_locales_and_without_defaultLocale(self):
        payload = self.payload(extra_req={
            'locales': {
                'de': {
                    'name': 'Die App',
                    'description': 'Eine Beschreibung für die App.'
                }
            }
        })
        req = self.request(iss=self.key, app_secret=self.secret,
                           payload=payload)
        form = VerifyForm({'req': req})
        assert not form.is_valid()

    def test_locales_and_with_defaultLocale(self):
        payload = self.payload(extra_req={
            'locales': {
                'de': {
                    'name': 'Die App',
                    'description': 'Eine Beschreibung für die App. Հ'
                }
            },
            'defaultLocale': 'en'
        })
        req = self.request(iss=self.key, app_secret=self.secret,
                           payload=payload)
        form = VerifyForm({'req': req})
        assert form.is_valid(), repr(form.errors)

    @mock.patch.object(settings, 'SHORT_FIELD_MAX_LENGTH', 255)
    def test_short_fields_too_long(self):
        for fn in ('chargebackURL',
                   'defaultLocale',
                   'id',
                   'name',
                   'postbackURL',
                   'productData'):
            payload = self.payload(extra_req={
                fn: 'x' * 256
            })
            req = self.request(payload=payload)
            form = VerifyForm({'req': req})
            assert not form.is_valid(), (
                'Field {0} gets too long error'.format(fn))
