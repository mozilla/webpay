# -*- coding: utf-8 -*-
import json
import time
from collections import defaultdict
from datetime import datetime

from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist

import mock
from curling.lib import HttpServerError
from mozpay.exc import RequestExpired
from nose.tools import eq_, ok_, raises
from pyquery import PyQuery as pq

from lib.marketplace.api import UnknownPricePoint
from lib.solitude import constants

from webpay.base import dev_messages as msg
from webpay.base.tests import BasicSessionCase
from webpay.pay import get_payment_url
from webpay.pay.samples import JWTtester

from . import Base, sample


@mock.patch.object(settings, 'KEY', 'marketplace.mozilla.org')
@mock.patch.object(settings, 'SECRET', 'marketplace.secret')
@mock.patch.object(settings, 'ISSUER', 'marketplace.mozilla.org')
@mock.patch.object(settings, 'INAPP_KEY_PATHS', {None: sample})
@mock.patch.object(settings, 'DEBUG', True)
class TestVerify(Base):

    def setUp(self):
        super(TestVerify, self).setUp()
        self.patches = []
        patch = mock.patch('webpay.pay.tasks.configure_transaction')
        self.configure_transaction = patch.start()
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

    @mock.patch('webpay.pay.views.solitude')
    def test_get(self, solitude):
        solitude.get_transaction.side_effect = ObjectDoesNotExist
        eq_(self.client.get(self.url).status_code, 400)

    @mock.patch('webpay.pay.views.solitude')
    def test_get_no_req(self, solitude):
        # Setting this is the minimum needed to simulate that you've already
        # started a transaction.
        solitude.get_transaction.return_value = {'notes': {}}
        eq_(self.client.get(self.url).status_code, 200)

    @mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
    @mock.patch('lib.marketplace.api.MarketplaceAPI.get_price')
    def test_inapp(self, get_price, get_active_product):
        self.set_secret(get_active_product)
        payload = self.request(iss=self.key, app_secret=self.secret)
        eq_(self.get(payload).status_code, 200)

    @mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
    @mock.patch('lib.marketplace.api.MarketplaceAPI.get_price')
    @mock.patch('webpay.auth.utils.update_session')
    def test_recently_entered_pin_redirect(self, update_session, get_price,
                                           get_active_product):
        self.set_secret(get_active_product)
        self.session['uuid'] = 'something'
        self.session['last_pin_success'] = datetime.now()
        self.save_session()
        payload = self.request(iss=self.key, app_secret=self.secret)
        res = self.get(payload)
        eq_(res.status_code, 302)
        assert res['Location'].endswith(
            '?next={0}'.format(get_payment_url(mock.Mock(session={})))
        ), res['Location']

    @mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
    @mock.patch('lib.marketplace.api.MarketplaceAPI.get_price')
    @mock.patch('lib.solitude.api.SolitudeAPI.set_needs_pin_reset')
    @mock.patch('webpay.auth.utils.update_session')
    def test_reset_flag_true(self, update_session, set_needs_pin_reset,
                             get_price, get_active_product):
        self.set_secret(get_active_product)
        # To appease has_pin
        self.session['uuid_has_pin'] = True
        self.session['uuid_has_confirmed_pin'] = True

        self.session['uuid_needs_pin_reset'] = True
        self.session['uuid'] = 'some:uuid'
        self.save_session()
        payload = self.request(iss=self.key, app_secret=self.secret)
        res = self.get(payload)
        eq_(res.status_code, 200)
        assert update_session.called
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

    @mock.patch.object(settings, 'PRODUCT_DESCRIPTION_LENGTH', 255)
    def test_truncate_long_description(self):
        payjwt = self.payload()
        payjwt['request']['description'] = 'x' * 256
        payload = self.request(payload=payjwt)
        eq_(self.get(payload).status_code, 200)
        req = self.client.session['notes']['pay_request']['request']
        eq_(len(req['description']), 255)
        assert req['description'].endswith('...'), 'ellipsis added'

    @mock.patch.object(settings, 'PRODUCT_DESCRIPTION_LENGTH', 255)
    def test_truncate_long_locale_description(self):
        payjwt = self.payload()
        payjwt['request']['defaultLocale'] = 'en'
        payjwt['request']['locales'] = {
            'it': {
                'description': 'x' * 256
            }
        }
        payload = self.request(payload=payjwt)
        eq_(self.get(payload).status_code, 200)
        req = self.client.session['notes']['pay_request']['request']
        eq_(len(req['locales']['it']['description']), 255)

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
        res = self.get(self.request())
        self.assertContains(res, msg.MALFORMED_URL, status_code=400)
        doc = pq(res.content)
        eq_(doc('body').attr('data-error-code'), msg.MALFORMED_URL)

    @mock.patch.object(settings, 'ALLOW_ANDROID_PAYMENTS', False)
    def test_disallow_android_payments(self):
        # Android Nightly agent:
        ua = 'Mozilla/5.0 (Android; Mobile; rv:31.0) Gecko/31.0 Firefox/31.0'
        res = self.get(self.request(), HTTP_USER_AGENT=ua)
        self.assertContains(res, msg.PAY_DISABLED, status_code=503)
        doc = pq(res.content)
        eq_(doc('body').attr('data-error-code'), msg.PAY_DISABLED)

    @mock.patch.object(settings, 'ALLOW_ANDROID_PAYMENTS', False)
    def test_allow_non_android_payments(self):
        # B2G agent:
        ua = 'Mozilla/5.0 (Mobile; rv:18.1) Gecko/20131009 Firefox/18.1'
        res = self.get(self.request(), HTTP_USER_AGENT=ua)
        eq_(res.status_code, 200)

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

    @mock.patch('webpay.pay.views.verify_jwt')
    def test_request_expired(self, verify):
        verify.side_effect = RequestExpired({})
        payload = self.request(app_secret=self.secret)
        res = self.get(payload)
        eq_(res.status_code, 400)
        # Output should show exception message.
        self.assertContains(res, msg.EXPIRED_JWT,
                            status_code=400)

    def test_only_simulations(self):
        with self.settings(ONLY_SIMULATIONS=True):
            res = self.get(self.request())
            self.assertContains(res, 'temporarily disabled', status_code=503)

    def test_begin_simulation(self):
        payjwt = self.payload()
        payjwt['request']['simulate'] = {'result': 'postback'}
        payload = self.request(payload=payjwt)
        res = self.get(payload)
        eq_(res.status_code, 200)
        self.assertTemplateUsed(res, 'pay/simulate.html')
        eq_(self.client.session['is_simulation'], True)
        assert not self.configure_transaction.called, (
            'configure_transaction should not be called when simulating')

    @mock.patch('webpay.auth.utils.client')
    @mock.patch('webpay.pay.views.check_pin_status')
    @mock.patch('webpay.pay.views.solitude')
    def test_start_pay_when_logged_in(self, api, check_pin, client):
        client.get_buyer.return_value = defaultdict(lambda: '<stub>')
        check_pin.return_value = None
        # This is a repeat purchase scenario. We call start_pay because login
        # will not call it for this scenario.
        self.session['uuid'] = 'some-email-token'
        self.save_session()
        payload = self.request(payload=self.payload())
        res = self.get(payload)
        eq_(res.status_code, 200)
        assert self.configure_transaction.called, (
            'lobby should configure_transaction when user is logged in')

    def test_begin_simulation_when_payments_disabled(self):
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
        self.assertContains(res, msg.BAD_SIM_RESULT,
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
        self.assertContains(res, msg.NO_SIM_REASON,
                            status_code=400)

    def test_bad_signature_does_not_store_simulation(self):
        payjwt = self.payload()
        payjwt['request']['simulate'] = {'result': 'postback'}
        payload = self.request(payload=payjwt,
                               app_secret=self.secret + '.nope')
        eq_(self.get(payload).status_code, 400)
        keys = self.client.session.keys()
        assert 'is_simulation' not in keys, keys

    def test_simulate_disabled_in_settings(self):
        payjwt = self.payload()
        payjwt['request']['simulate'] = {'result': 'postback'}
        payload = self.request(payload=payjwt)
        with self.settings(ALLOW_SIMULATE=False):
            res = self.get(payload)
        self.assertContains(res, msg.SIM_DISABLED,
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

    def test_logout_timeout_data_attr(self):
        with self.settings(LOGOUT_TIMEOUT=300, TEST_PIN_UI=True):
            res = self.client.get(self.url)
        ok_('data-logout-timeout="300"' in res.content)

    def test_wrong_icons_type(self):
        payjwt = self.payload()
        payjwt['request']['icons'] = '...'  # must be a dict
        payload = self.request(payload=payjwt)
        res = self.get(payload)
        self.assertContains(res, msg.BAD_ICON_KEY,
                            status_code=400)

    def test_bad_icon_url(self):
        payjwt = self.payload()
        payjwt['request']['icons'] = {'64': 'not-a-url'}
        payload = self.request(payload=payjwt)
        eq_(self.get(payload).status_code, 400)

    @mock.patch.object(settings, 'ALLOWED_CALLBACK_SCHEMES', ['https'])
    def test_http_icon_url_ok(self):
        payjwt = self.payload()
        payjwt['request']['icons'] = {'64': 'http://foo.com/icon.png'}
        payjwt['request']['postbackURL'] = 'https://foo.com/postback'
        payjwt['request']['chargebackURL'] = 'https://foo.com/chargeback'
        payload = self.request(payload=payjwt)
        eq_(self.get(payload).status_code, 200)

    def test_invalid_price_point(self):
        price = self.mkt.get_price
        price.side_effect = UnknownPricePoint
        payload = self.request(payload=self.payload())
        res = self.get(payload)
        assert price.called
        self.assertContains(res, msg.BAD_PRICE_POINT, status_code=400)

    @raises(HttpServerError)
    def test_internal_error(self):
        price = self.mkt.get_price
        price.side_effect = HttpServerError
        payload = self.request(payload=self.payload())
        self.get(payload)


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
        self.save_session()

    @mock.patch.object(settings, 'PAY_URLS',
                       {'bango': {'base': 'http://bango',
                                  'pay': '/pay?bcid={uid_pay}'}})
    def test_redirect_when_ready(self, get_transaction):
        get_transaction.return_value = {
            'status': constants.STATUS_PENDING,
            'uid_pay': 123,
        }
        self.session['payment_start'] = time.time()
        self.save_session()
        res = self.client.get(self.wait)
        eq_(res['Location'], 'http://bango/pay?bcid=123')

    @mock.patch.object(settings, 'PAYMENT_PROVIDER', 'reference')
    def test_universal_redirect_when_ready(self, get_transaction):
        get_transaction.return_value = {
            'status': constants.STATUS_PENDING,
            'uid_pay': 123,
        }
        self.session['payment_start'] = time.time()
        self.save_session()
        with mock.patch.object(settings, 'PAY_URLS',
                               {'reference': {'base': 'http://base',
                                              'pay': '/pay?t={uid_pay}'}}):
            res = self.client.get(self.wait)
        eq_(res['Location'], 'http://base/pay?t=123')

    @mock.patch.object(settings, 'PAY_URLS',
                       {'bango': {'base': 'http://bango',
                                  'pay': '/pay?bcid={uid_pay}'}})
    def test_start_ready(self, get_transaction):
        get_transaction.return_value = {
            'status': constants.STATUS_PENDING,
            'uid_pay': 123,
        }
        self.session['payment_start'] = time.time()
        self.save_session()
        res = self.client.get(self.start)
        eq_(res.status_code, 200, res.content)
        data = json.loads(res.content)
        eq_(data['url'], 'http://bango/pay?bcid=123')
        eq_(data['status'], constants.STATUS_PENDING)

    @mock.patch.object(settings, 'PAYMENT_PROVIDER', 'reference')
    def test_universal_start_ready(self, get_transaction):
        get_transaction.return_value = {
            'status': constants.STATUS_PENDING,
            'uid_pay': 123,
        }
        self.session['payment_start'] = time.time()
        self.save_session()
        with mock.patch.object(settings, 'PAY_URLS',
                               {'reference': {'base': 'http://base',
                                              'pay': '/pay?t={uid_pay}'}}):
            res = self.client.get(self.start)
        eq_(res.status_code, 200, res.content)
        data = json.loads(res.content)
        eq_(data['url'], 'http://base/pay?t=123')
        eq_(data['status'], constants.STATUS_PENDING)

    def test_start_not_there(self, get_transaction):
        get_transaction.side_effect = ObjectDoesNotExist
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
            self.assertContains(res, msg.TRANS_ENDED,
                                status_code=400)

    def test_wait_ended_transaction(self, get_transaction):
        for status in constants.STATUS_ENDED:
            self.wait_ended_transaction(get_transaction, status)

    def test_wait(self, get_transaction):
        res = self.client.get(self.wait)
        eq_(res.status_code, 200)
        self.assertContains(res, 'Setting up payment')


class TestPostback(Base):

    def setUp(self):
        super(TestPostback, self).setUp()
        self.callback_success = reverse('pay.callback_success_url')
        self.callback_error = reverse('pay.callback_error_url')

        path = 'lib.solitude.api.ProviderHelper.is_callback_token_valid'
        p = mock.patch(path)
        self.tok_check = p.start()
        self.addCleanup(p.stop)

    @mock.patch('webpay.pay.tasks.payment_notify')
    def test_callback_success(self, payment_notify):
        self.tok_check.return_value = True
        res = self.client.post(self.callback_success, {
            'signed_notice': 'foo=bar&ext_transaction_id=123'
        })
        eq_(res.status_code, 204)

    def test_callback_success_failure(self):
        self.tok_check.return_value = False
        res = self.client.post(self.callback_success, {
            'signed_notice': 'foo=bar&ext_transaction_id=123'
        })
        eq_(res.status_code, 400)

    def test_callback_success_incomplete(self):
        self.tok_check.return_value = True
        res = self.client.post(self.callback_success, {
            'signed_notice': 'foo=bar'
        })
        eq_(res.status_code, 400)

    @mock.patch('webpay.pay.tasks.chargeback_notify')
    def test_callback_error(self, chargeback_notify):
        self.tok_check.return_value = True
        res = self.client.post(self.callback_error, {
            'signed_notice': 'foo=bar&ext_transaction_id=123'
        })
        eq_(res.status_code, 204)

    def test_callback_error_failure(self):
        self.tok_check.return_value = False
        res = self.client.post(self.callback_error, {
            'signed_notice': 'foo=bar&ext_transaction_id=123'
        })
        eq_(res.status_code, 400)

    def test_callback_error_incomplete(self):
        self.tok_check.return_value = True
        res = self.client.post(self.callback_error, {
            'signed_notice': 'foo=bar'
        })
        eq_(res.status_code, 400)


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
        self.save_session()

        # Stub out non-simulate code in case it gets called.
        self.patches = [
            mock.patch('webpay.pay.tasks.configure_transaction'),
            mock.patch('webpay.pay.views.marketplace')
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_not_simulating(self):
        del self.session['is_simulation']
        self.save_session()
        eq_(self.client.post(self.simulate_url).status_code, 403)

    def test_false_simulation(self):
        self.session['is_simulation'] = False
        self.save_session()
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


@mock.patch('webpay.pay.views.tasks.simulate_notify')
class TestSuperSimulate(BasicSessionCase):

    def setUp(self):
        super(TestSuperSimulate, self).setUp()
        self.request = {'request': {}}
        self.session['trans_id'] = '<trans_id>'
        self.save_session()

        p = mock.patch('webpay.pay.views.solitude')
        self.solitude = p.start()
        self.addCleanup(p.stop)
        self.solitude.get_transaction.return_value = {
            'notes': {'issuer_key': '<issuer_key>',
                      'pay_request': self.request}
        }

    def set_perms(self, perms):
        self.session['mkt_permissions'] = perms
        self.save_session()

    def test_do_simulate(self, fake_notify):
        self.set_perms({'admin': False, 'reviewer': True})
        self.client.post(reverse('pay.super_simulate'))
        fake_notify.delay.assert_called_with('<issuer_key>', mock.ANY)
        req = fake_notify.delay.call_args[0][1]['request']
        eq_(req['simulate'], {'result': 'postback'})

    def test_invalid_permissions(self, fake_notify):
        self.set_perms({'admin': False, 'reviewer': False})
        res = self.client.post(reverse('pay.super_simulate'))
        eq_(res.status_code, 403)
        assert not fake_notify.delay.called


class TestBounce(Base):

    def setUp(self):
        super(TestBounce, self).setUp()
        self.url = reverse('pay.bounce')

    def test_good_next(self):
        res = self.client.get(self.url + '?next=/mozpay/')
        eq_(res.status_code, 200)

    def test_bad_next(self):
        res = self.client.get(self.url + '?next=http://google.com')
        eq_(res.status_code, 403)

    def test_missing_next(self):
        res = self.client.get(self.url)
        eq_(res.status_code, 403)
