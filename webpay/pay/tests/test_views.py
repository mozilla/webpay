# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime

from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist

import mock
from nose import SkipTest
from nose.tools import eq_

from lib.marketplace.api import UnknownPricePoint
from lib.solitude import constants

from webpay.base.tests import BasicSessionCase
from webpay.pay import get_payment_url
from webpay.pay.forms import VerifyForm
from webpay.pay.models import Issuer, ISSUER_ACTIVE, ISSUER_INACTIVE
from webpay.pay.samples import JWTtester

sample = os.path.join(os.path.dirname(__file__), 'sample.key')


class Base(BasicSessionCase, JWTtester):

    def setUp(self):
        super(Base, self).setUp()
        self.url = reverse('pay.lobby')
        self.key = 'public.key'
        self.secret = 'private.secret'
        self.create()

    def get(self, payload):
        return self.client.get('%s?req=%s' % (self.url, payload))

    def payload(self, **kw):
        kw.setdefault('iss', settings.KEY)
        return super(Base, self).payload(**kw)

    def request(self, **kw):
        # This simulates payment requests which do not have response.
        kw.setdefault('include_response', False)
        kw.setdefault('iss', settings.KEY)
        kw.setdefault('app_secret', settings.SECRET)
        return super(Base, self).request(**kw)

    def create(self, key=None, secret=None):
        key = key or self.key
        secret = secret or self.secret
        self.iss = Issuer.objects.create(issuer_key=key,
                                         status=ISSUER_ACTIVE)
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            self.iss.set_private_key(secret)

    def set_secret(self, get_active_product):
        get_active_product.return_value = {
            'secret': self.secret,
            'access': constants.ACCESS_PURCHASE
        }


@mock.patch.object(settings, 'KEY', 'marketplace.mozilla.org')
@mock.patch.object(settings, 'SECRET', 'marketplace.secret')
@mock.patch.object(settings, 'ISSUER', 'marketplace.mozilla.org')
@mock.patch.object(settings, 'INAPP_KEY_PATHS', {None: sample})
@mock.patch.object(settings, 'DEBUG', True)
class TestVerify(Base):

    def setUp(self):
        super(TestVerify, self).setUp()
        self.patches = []
        patch = mock.patch('webpay.pay.views.tasks.start_pay')
        self.start_pay = patch.start()
        self.patches.append(patch)
        patch = mock.patch('webpay.pay.views.marketplace')
        self.mkt = patch.start()
        self.patches.append(patch)

    def tearDown(self):
        super(TestVerify, self).tearDown()
        for p in self.patches:
            p.stop()

    def test_post(self):
        eq_(self.client.post(self.url).status_code, 405)

    def test_get(self):
        eq_(self.client.get(self.url).status_code, 400)

    def test_get_no_req(self):
        # Setting this is the minimum needed to simulate that you've already
        # started a transaction.
        self.session['notes'] = {}
        self.session.save()
        eq_(self.client.get(self.url).status_code, 200)

    @mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
    @mock.patch('lib.marketplace.api.MarketplaceAPI.get_price')
    def test_inapp(self, get_price, get_active_product):
        self.set_secret(get_active_product)
        payload = self.request(iss=self.key, app_secret=self.secret)
        eq_(self.get(payload).status_code, 200)

    @mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
    @mock.patch('lib.marketplace.api.MarketplaceAPI.get_price')
    def test_recently_entered_pin_redirect(self, get_price,
                                           get_active_product):
        self.set_secret(get_active_product)
        self.session['uuid'] = 'something'
        self.session['last_pin_success'] = datetime.now()
        self.session.save()
        payload = self.request(iss=self.key, app_secret=self.secret)
        res = self.get(payload)
        eq_(res.status_code, 302)
        assert res['Location'].endswith(get_payment_url())

    @mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
    @mock.patch('lib.marketplace.api.MarketplaceAPI.get_price')
    @mock.patch('lib.solitude.api.SolitudeAPI.set_needs_pin_reset')
    def test_reset_flag_true(self, set_needs_pin_reset,
                             get_price, get_active_product):
        self.set_secret(get_active_product)
        # To appease has_pin
        self.session['uuid_has_pin'] = True
        self.session['uuid_has_confirmed_pin'] = True

        self.session['uuid_needs_pin_reset'] = True
        self.session['uuid'] = 'some:uuid'
        self.session.save()
        payload = self.request(iss=self.key, app_secret=self.secret)
        res = self.get(payload)
        eq_(res.status_code, 200)
        assert set_needs_pin_reset.called

    @mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
    def test_inapp_wrong_secret(self, get_active_product):
        self.set_secret(get_active_product)
        payload = self.request(iss=self.key, app_secret=self.secret + '.nope')
        eq_(self.get(payload).status_code, 400)

    @mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
    def test_inapp_wrong_key(self, get_active_product):
        get_active_product.side_effect = ObjectDoesNotExist
        payload = self.request(iss=self.key + '.nope', app_secret=self.secret)
        eq_(self.get(payload).status_code, 400)

    def test_bad_payload(self):
        eq_(self.get('foo').status_code, 400)

    def test_unicode_payload(self):
        eq_(self.get(u'Հ').status_code, 400)

    def test_missing_tier(self):
        payjwt = self.payload()
        del payjwt['request']['pricePoint']
        payload = self.request(payload=payjwt)
        eq_(self.get(payload).status_code, 400)

    def test_empty_tier(self):
        payjwt = self.payload()
        payjwt['request']['pricePoint'] = ''
        payload = self.request(payload=payjwt)
        eq_(self.get(payload).status_code, 400)

    def test_missing_description(self):
        payjwt = self.payload()
        del payjwt['request']['description']
        payload = self.request(payload=payjwt)
        eq_(self.get(payload).status_code, 400)

    def test_missing_name(self):
        payjwt = self.payload()
        del payjwt['request']['name']
        payload = self.request(payload=payjwt)
        eq_(self.get(payload).status_code, 400)

    def test_missing_url(self):
        for url in ['postbackURL', 'chargebackURL']:
            payjwt = self.payload()
            del payjwt['request'][url]
            payload = self.request(payload=payjwt)
            eq_(self.get(payload).status_code, 400)

    @mock.patch.object(settings, 'ALLOWED_CALLBACK_SCHEMES', ['https'])
    def test_non_https_url(self):
        with self.settings(VERBOSE_LOGGING=True):
            res = self.get(self.request())
            self.assertContains(res, 'Schema must be', status_code=400)

    @mock.patch.object(settings, 'ALLOWED_CALLBACK_SCHEMES', ['https'])
    def test_non_https_url_ok_for_simulation(self):
        payjwt = self.payload()
        payjwt['request']['simulate'] = {'result': 'postback'}
        res = self.get(self.request(payload=payjwt))
        eq_(res.status_code, 200)

    def test_bad_url(self):
        payjwt = self.payload()
        payjwt['request']['postbackURL'] = 'fooey!'
        payload = self.request(payload=payjwt)
        eq_(self.get(payload).status_code, 400)

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

    def test_only_simulations(self):
        with self.settings(ONLY_SIMULATIONS=True):
            res = self.get(self.request())
            self.assertContains(res, 'temporarily disabled', status_code=503)

    @mock.patch('webpay.pay.views.tasks.start_pay')
    def test_begin_simulation(self, start_pay):
        payjwt = self.payload()
        payjwt['request']['simulate'] = {'result': 'postback'}
        payload = self.request(payload=payjwt)
        res = self.get(payload)
        eq_(res.status_code, 200)
        self.assertTemplateUsed(res, 'pay/simulate.html')
        eq_(self.client.session['is_simulation'], True)
        assert not start_pay.delay.called, (
            'start_pay should not be called when simulating')

    @mock.patch('webpay.pay.views.tasks.start_pay')
    def test_begin_simulation_when_payments_disabled(self, start_pay):
        payjwt = self.payload()
        payjwt['request']['simulate'] = {'result': 'postback'}
        payload = self.request(payload=payjwt)
        with self.settings(ONLY_SIMULATIONS=True):
            res = self.get(payload)
        eq_(res.status_code, 200)
        eq_(self.client.session['is_simulation'], True)

    def test_unknown_simulation(self):
        payjwt = self.payload()
        payjwt['request']['simulate'] = {'result': '<script>alert()</script>'}
        payload = self.request(payload=payjwt)
        res = self.get(payload)
        self.assertContains(res,
                            'simulation result is not supported',
                            status_code=400)

    def test_empty_simulation(self):
        payjwt = self.payload()
        payjwt['request']['simulate'] = {}
        payload = self.request(payload=payjwt)
        eq_(self.get(payload).status_code, 200)
        eq_(self.client.session['is_simulation'], False)

    def test_incomplete_chargeback_simulation(self):
        payjwt = self.payload()
        payjwt['request']['simulate'] = {'result': 'chargeback'}
        payload = self.request(payload=payjwt)
        res = self.get(payload)
        self.assertContains(res, 'simulation is missing the key',
                            status_code=400)

    def test_bad_signature_does_not_store_simulation(self):
        payjwt = self.payload()
        payjwt['request']['simulate'] = {'result': 'postback'}
        payload = self.request(payload=payjwt,
                               app_secret=self.secret + '.nope')
        eq_(self.get(payload).status_code, 400)
        keys = self.client.session.keys()
        assert 'is_simulation' not in keys, keys

    def test_debug_when_simulating(self):
        with self.settings(VERBOSE_LOGGING=False):
            payjwt = self.payload()
            payjwt['request']['simulate'] = {'result': 'postback'}
            payload = self.request(payload=payjwt,
                                   app_secret=self.secret + '.nope')
            res = self.get(payload)
            eq_(res.status_code, 400)
            # Output should show exception message.
            self.assertContains(res,
                                'InvalidJWT: Signature verification failed',
                                status_code=400)

    def test_simulate_disabled_in_settings(self):
        payjwt = self.payload()
        payjwt['request']['simulate'] = {'result': 'postback'}
        payload = self.request(payload=payjwt)
        with self.settings(ALLOW_SIMULATE=False):
            res = self.get(payload)
        self.assertContains(res,
                            'simulations are disabled',
                            status_code=400)

    @mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
    def test_incorrect_simulation(self, get_active_product):
        get_active_product.return_value = {'secret': self.secret,
                                           'access': constants.ACCESS_SIMULATE}
        # Make a regular request, not a simulation.
        payload = self.request(iss='third-party-app')
        eq_(self.get(payload).status_code, 400)

    def test_pin_ui(self):
        with self.settings(TEST_PIN_UI=True):
            res = self.client.get(self.url)
        eq_(res.status_code, 200)
        self.assertTemplateUsed(res, 'pay/lobby.html')

    def test_wrong_icons_type(self):
        payjwt = self.payload()
        payjwt['request']['icons'] = '...'  # must be a dict
        payload = self.request(payload=payjwt)
        with self.settings(VERBOSE_LOGGING=True):
            res = self.get(payload)
        self.assertContains(res, 'must be an object of URLs',
                            status_code=400)

    def test_bad_icon_url(self):
        payjwt = self.payload()
        payjwt['request']['icons'] = {'64': 'not-a-url'}
        payload = self.request(payload=payjwt)
        eq_(self.get(payload).status_code, 400)

    def test_invalid_price_point(self):
        price = self.mkt.get_price
        price.side_effect = UnknownPricePoint
        payload = self.request(payload=self.payload())
        res = self.get(payload)
        assert price.called
        eq_(res.status_code, 400)


# TODO(wraithan): Move to its own file like we do other places.
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


@mock.patch('lib.solitude.api.client.get_transaction')
class TestWaitToStart(Base):

    def setUp(self):
        super(TestWaitToStart, self).setUp()
        self.wait = reverse('pay.wait_to_start')
        self.start = reverse('pay.trans_start_url')

        # Log in.
        self.session['uuid'] = 'verified-user'
        # Start a payment.
        self.session['trans_id'] = 'some:trans'
        self.session.save()

    @mock.patch.object(settings, 'BANGO_PAY_URL', 'http://bango/pay?bcid=%s')
    def test_redirect_when_ready(self, get_transaction):
        get_transaction.return_value = {
            'status': constants.STATUS_PENDING,
            'uid_pay': 123,
        }
        res = self.client.get(self.wait)
        eq_(res['Location'], settings.BANGO_PAY_URL % 123)

    @mock.patch.object(settings, 'BANGO_PAY_URL', 'http://bango/pay?bcid=%s')
    def test_start_ready(self, get_transaction):
        get_transaction.return_value = {
            'status': constants.STATUS_PENDING,
            'uid_pay': 123,
        }
        res = self.client.get(self.start)
        eq_(res.status_code, 200, res.content)
        data = json.loads(res.content)
        eq_(data['url'], settings.BANGO_PAY_URL % 123)
        eq_(data['status'], constants.STATUS_PENDING)

    def test_start_not_there(self, get_transaction):
        get_transaction.side_effect = ValueError
        res = self.client.get(self.start)
        eq_(res.status_code, 200, res.content)
        data = json.loads(res.content)
        eq_(data['url'], None)
        eq_(data['status'], None)

    def test_start_not_ready(self, get_transaction):
        get_transaction.return_value = {
            'status': constants.STATUS_RECEIVED,
            'uid_pay': 123,
        }
        res = self.client.get(self.start)
        eq_(res.status_code, 200, res.content)
        data = json.loads(res.content)
        eq_(data['url'], None)
        eq_(data['status'], constants.STATUS_RECEIVED)

    def wait_ended_transaction(self, get_transaction, status):
        with self.settings(VERBOSE_LOGGING=True):
            get_transaction.return_value = {
                'status': status,
                'uid_pay': 123,
            }
            res = self.client.get(self.wait)
            self.assertContains(res,
                                'Transaction has already ended.',
                                status_code=400)

    def test_wait_ended_transaction(self, get_transaction):
        for status in constants.STATUS_ENDED:
            self.wait_ended_transaction(get_transaction, status)

    def test_wait(self, get_transaction):
        res = self.client.get(self.wait)
        eq_(res.status_code, 200)
        self.assertContains(res, 'Waiting')


class TestSimulate(BasicSessionCase, JWTtester):

    def setUp(self):
        super(TestSimulate, self).setUp()
        self.url = reverse('pay.lobby')
        self.simulate_url = reverse('pay.simulate')
        self.session['is_simulation'] = True
        self.session['notes'] = {}
        self.issuer_key = 'some-app-id'
        self.session['notes']['issuer_key'] = self.issuer_key
        req = self.payload()
        req['request']['simulate'] = {'result': 'postback'}
        self.session['notes']['pay_request'] = req
        self.session.save()
        # Stub out non-simulate code in case it gets called.
        self.patches = [
            mock.patch('webpay.pay.views.tasks.start_pay'),
            mock.patch('webpay.pay.views.marketplace')
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_not_simulating(self):
        del self.session['is_simulation']
        self.session.save()
        eq_(self.client.post(self.simulate_url).status_code, 403)

    def test_false_simulation(self):
        self.session['is_simulation'] = False
        self.session.save()
        eq_(self.client.post(self.simulate_url).status_code, 403)

    def test_simulate(self):
        res = self.client.get(self.url)
        eq_(res.status_code, 200)
        eq_(res.context['simulate'],
            self.session['notes']['pay_request']['request']['simulate'])

    @mock.patch('webpay.pay.views.tasks.simulate_notify')
    def test_simulate_postback(self, notify):
        res = self.client.post(self.simulate_url)
        notify.delay.assert_called_with(self.issuer_key,
                                        self.session['notes']['pay_request'])
        self.assertTemplateUsed(res, 'pay/simulate_done.html')
