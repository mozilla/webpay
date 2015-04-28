# -*- coding: utf-8 -*-
import json
import time

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.test.utils import override_settings

import mock
from curling.lib import HttpServerError
from mozpay.exc import RequestExpired
from nose.tools import eq_, ok_, raises

from lib.marketplace.api import UnknownPricePoint
from lib.solitude import constants
from lib.solitude.constants import STATUS_PENDING
from webpay.api.tests.base import BaseAPICase
from webpay.base import dev_messages as msg
from webpay.pay.tests import Base, sample


@override_settings(
    KEY='marketplace.mozilla.org', SECRET='marketplace.secret', DEBUG=True,
    ISSUER='marketplace.mozilla.org', INAPP_KEY_PATHS={None: sample})
class PayTester(Base, BaseAPICase):

    def setUp(self):
        super(PayTester, self).setUp()
        self.url = reverse('api:pay')

        p = mock.patch('webpay.pay.tasks.start_pay')
        self.start_pay = p.start()
        self.addCleanup(p.stop)

        p = mock.patch('webpay.pay.tasks.client')
        self.api_client = p.start()
        self.addCleanup(p.stop)
        self.api_client.get_transaction.return_value = {
            'uuid': 'uuid',
            'status': STATUS_PENDING,
            'notes': {}
        }

        p = mock.patch('webpay.pay.views.marketplace')
        self.mkt = p.start()
        self.addCleanup(p.stop)

    def assert_error_code(self, res, code, status=400):
        eq_(res.status_code, status, res)
        eq_(json.loads(res.content)['error_code'], code)

    def post(self, data=None, req=None, mcc='423', mnc='555',
             request_kwargs=None, **kwargs):
        if data is None:
            data = {}
            if req is None:
                req = self.request(**(request_kwargs or {}))
            data = {'req': req}
            if mnc:
                data['mnc'] = mnc
            if mcc:
                data['mcc'] = mcc
        kwargs.setdefault('HTTP_ACCEPT', 'application/json')
        return self.client.post(self.url, data=data, **kwargs)


class TestPay(PayTester):

    def test_configures_transaction_success(self):
        res = self.post()
        eq_(res.status_code, 200)
        data = json.loads(res.content)
        eq_(data['status'], 'ok')
        eq_(data['simulation'], None)

    @mock.patch('webpay.pay.tasks.configure_transaction')
    def test_configuration_failure(self, configure):
        configure.return_value = (False, 'FAIL_CODE')
        res = self.post()
        self.assert_error_code(res, 'FAIL_CODE')

    @mock.patch('webpay.pay.tasks.configure_transaction')
    def test_configuration_failure_without_code(self, configure):
        configure.return_value = (False, None)
        res = self.post()
        self.assert_error_code(res, msg.TRANS_CONFIG_FAILED)

    @mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
    def test_configure_inapp_payment(self, get_active_product):
        self.solitude.generic.product.get_object.return_value = {
            'secret': 'p.secret', 'access': constants.ACCESS_PURCHASE}
        self.set_secret(get_active_product)
        res = self.post(request_kwargs=dict(iss=self.key,
                                            app_secret=self.secret))
        eq_(res.status_code, 200)
        data = json.loads(res.content)
        eq_(data['status'], 'ok')
        eq_(data['simulation'], None)

    @mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
    def test_inapp_wrong_secret(self, get_active_product):
        self.solitude.generic.product.get_object.return_value = {
            'secret': 'p.secret', 'access': constants.ACCESS_PURCHASE}
        self.set_secret(get_active_product)
        res = self.post(request_kwargs=dict(iss=self.key,
                                            app_secret=self.secret + 'nope'))
        eq_(res.status_code, 400, res)

    @mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
    def test_inapp_wrong_key(self, get_active_product):
        get_active_product.side_effect = ObjectDoesNotExist
        self.solitude.generic.product.get_object.return_value = {
            'secret': 'p.secret', 'access': constants.ACCESS_PURCHASE}
        res = self.post(request_kwargs=dict(iss=self.key + '.nope',
                                            app_secret=self.secret))
        eq_(res.status_code, 400, res)

    @mock.patch.object(settings, 'PRODUCT_DESCRIPTION_LENGTH', 255)
    def test_truncate_long_locale_description(self):
        payjwt = self.payload()
        payjwt['request']['defaultLocale'] = 'en'
        payjwt['request']['locales'] = {
            'it': {
                'description': 'x' * 257
            }
        }
        req = self.request(payload=payjwt)
        res = self.post(req=req)

        eq_(res.status_code, 200)
        req = self.client.session['notes']['pay_request']['request']
        eq_(len(req['locales']['it']['description']), 255)

    @mock.patch.object(settings, 'PRODUCT_DESCRIPTION_LENGTH', 255)
    def test_truncate_long_description(self):
        payjwt = self.payload()
        payjwt['request']['description'] = 'x' * 257
        req = self.request(payload=payjwt)
        res = self.post(req=req)

        eq_(res.status_code, 200)
        req = self.client.session['notes']['pay_request']['request']
        eq_(len(req['description']), 255)
        assert req['description'].endswith('...'), 'ellipsis added'

    def test_partial_locale_data(self):
        payjwt = self.payload()
        payjwt['request']['defaultLocale'] = 'en'
        payjwt['request']['locales'] = {
            'it': {
                'name': 'Some Name'
                # This is intentionally missing a description.
            }
        }
        req = self.request(payload=payjwt)
        # This was raising a KeyError. See bug 1140484.
        res = self.post(req=req)
        eq_(res.status_code, 200)

    def test_paid_product(self):
        req = self.request(
            payload=self.payload(extra_req={'pricePoint': '1'}))
        res = self.post(req=req)
        eq_(res.status_code, 200)
        data = json.loads(res.content)
        eq_(data['payment_required'], True)

    def test_free_product(self):
        p = mock.patch('webpay.pay.tasks.free_notify.delay')
        self.free_task = p.start()
        self.addCleanup(p.stop)
        req = self.request(
            payload=self.payload(extra_req={'pricePoint': '0'}))
        res = self.post(req=req)
        eq_(res.status_code, 200)
        data = json.loads(res.content)
        ok_(self.free_task.called)
        eq_(data['payment_required'], False)

    def test_no_mnc_mcc_ok(self):
        res = self.post(mcc='', mnc='')
        eq_(res.status_code, 200)
        args = self.start_pay.delay.call_args[0][1]
        eq_(args['network'], {})

    def test_stores_mnc_mcc(self):
        res = self.post(mnc='423', mcc='555')
        eq_(res.status_code, 200)
        args = self.start_pay.delay.call_args[0][1]
        eq_(args['network'], {'mnc': '423', 'mcc': '555'})

    def test_non_ascii_form_error(self):
        # This was triggering a non-ascii error in a logger.
        self.post(mnc=None, mcc=None, HTTP_ACCEPT_LANGUAGE='zh-CN')

    @mock.patch.object(settings, 'SIMULATED_NETWORK',
                       {'mcc': '123', 'mnc': '45'})
    def test_simulate_network(self):
        # Pretend this is the client posting a real
        # network or maybe NULLs.
        self.post(mcc='111', mnc='01')
        # Make sure the posted network was overridden.
        eq_(self.start_pay.delay.call_args[0][1]['network'],
            {'mcc': '123', 'mnc': '45'})

    @mock.patch.object(settings, 'ALLOWED_CALLBACK_SCHEMES', ['https'])
    def test_http_icon_url_ok(self):
        payjwt = self.payload()
        payjwt['request']['icons'] = {'64': 'http://foo.com/icon.png'}
        payjwt['request']['postbackURL'] = 'https://foo.com/postback'
        payjwt['request']['chargebackURL'] = 'https://foo.com/chargeback'
        payload = self.request(payload=payjwt)
        eq_(self.post(req=payload).status_code, 200)


class TestBadPayRequests(PayTester):

    def test_missing_jwt(self):
        res = self.post(data={})
        eq_(res.status_code, 400)

    def test_bad_jwt(self):
        self.assert_error_code(self.post(req='not-a-jwt'),
                               msg.JWT_DECODE_ERR)

    def test_non_ascii_jwt(self):
        self.assert_error_code(self.post(req=u'Հ'), msg.JWT_DECODE_ERR)

    def test_missing_tier(self):
        payjwt = self.payload()
        del payjwt['request']['pricePoint']
        res = self.post(request_kwargs=dict(payload=payjwt))
        self.assert_error_code(res, msg.INVALID_JWT)

    def test_empty_tier(self):
        payjwt = self.payload()
        payjwt['request']['pricePoint'] = ''
        res = self.post(request_kwargs=dict(payload=payjwt))
        self.assert_error_code(res, msg.INVALID_JWT)

    def test_missing_description(self):
        payjwt = self.payload()
        del payjwt['request']['description']
        res = self.post(request_kwargs=dict(payload=payjwt))
        self.assert_error_code(res, msg.INVALID_JWT)

    def test_missing_name(self):
        payjwt = self.payload()
        del payjwt['request']['name']
        res = self.post(request_kwargs=dict(payload=payjwt))
        self.assert_error_code(res, msg.INVALID_JWT)

    def test_missing_url(self):
        for url in ['postbackURL', 'chargebackURL']:
            payjwt = self.payload()
            del payjwt['request'][url]
            res = self.post(request_kwargs=dict(payload=payjwt))
            self.assert_error_code(res, msg.INVALID_JWT)

    @mock.patch.object(settings, 'ALLOWED_CALLBACK_SCHEMES', ['https'])
    def test_non_https_url(self):
        res = self.post()
        self.assert_error_code(res, msg.MALFORMED_URL)

    def test_bad_url(self):
        payjwt = self.payload()
        payjwt['request']['postbackURL'] = 'fooey!'
        res = self.post(request_kwargs=dict(payload=payjwt))
        self.assert_error_code(res, msg.MALFORMED_URL)

    def test_wrong_icons_type(self):
        payjwt = self.payload()
        payjwt['request']['icons'] = '...'  # must be a dict
        res = self.post(request_kwargs=dict(payload=payjwt))
        self.assert_error_code(res, msg.BAD_ICON_KEY)

    def test_bad_icon_url(self):
        payjwt = self.payload()
        payjwt['request']['icons'] = {'64': 'not-a-url'}
        res = self.post(request_kwargs=dict(payload=payjwt))
        self.assert_error_code(res, msg.MALFORMED_URL)

    @mock.patch('webpay.pay.views.verify_jwt')
    def test_request_expired(self, verify):
        verify.side_effect = RequestExpired({})
        res = self.post()
        self.assert_error_code(res, msg.EXPIRED_JWT)

    def test_invalid_mcc(self):
        accept = 'application/json, text/javascript, */*; q=0.01'
        res = self.post(mcc='abc', HTTP_ACCEPT=accept)
        eq_(res.status_code, 400)
        errors = json.loads(res.content)
        ok_('error_code' in errors)

    def test_missing_mcc(self):
        res = self.post(mcc=None)
        eq_(res.status_code, 400)

    def test_unsupported_jwt_algorithm(self):
        with self.settings(SUPPORTED_JWT_ALGORITHMS=['HS384']):
            res = self.post(
                request_kwargs={'jwt_kwargs': {'algorithm': 'HS256'}})
        self.assert_error_code(res, msg.INVALID_JWT)

    def test_invalid_price_point(self):
        price = self.mkt.get_price
        price.side_effect = UnknownPricePoint
        res = self.post()
        assert price.called
        self.assert_error_code(res, msg.BAD_PRICE_POINT)

    @raises(HttpServerError)
    def test_price_api_must_work(self):
        price = self.mkt.get_price
        price.side_effect = HttpServerError
        self.post()


class TestPaymentsDisabled(PayTester):

    @mock.patch.object(settings, 'ALLOW_ANDROID_PAYMENTS', False)
    def test_disallow_android_payments(self):
        # Android Nightly agent on a phone:
        ua = 'Mozilla/5.0 (Android; Mobile; rv:31.0) Gecko/31.0 Firefox/31.0'
        res = self.post(HTTP_USER_AGENT=ua)
        self.assert_error_code(res, msg.PAY_DISABLED, status=503)

    @mock.patch.object(settings, 'ALLOW_ANDROID_PAYMENTS', False)
    def test_disallow_android_tablet_payments(self):
        # Android Nightly agent on a tablet:
        ua = 'Mozilla/5.0 (Android; Tablet; rv:31.0) Gecko/31.o Firefox/31.0'
        res = self.post(HTTP_USER_AGENT=ua)
        self.assert_error_code(res, msg.PAY_DISABLED, status=503)

    @mock.patch.object(settings, 'ALLOW_ANDROID_PAYMENTS', False)
    def test_allow_non_android_payments(self):
        # B2G agent:
        ua = 'Mozilla/5.0 (Mobile; rv:18.1) Gecko/20131009 Firefox/18.1'
        res = self.post(HTTP_USER_AGENT=ua)
        eq_(res.status_code, 200)

    @mock.patch.object(settings, 'ALLOW_TARAKO_PAYMENTS', False)
    def test_disallow_tarako_payments(self):
        ua = 'Mozilla/5.0 (Mobile; rv:28.1) Gecko/28.1 Firefox 28.1'
        res = self.post(HTTP_USER_AGENT=ua)
        self.assert_error_code(res, msg.PAY_DISABLED, status=503)

    @mock.patch.object(settings, 'ALLOW_TARAKO_PAYMENTS', True)
    def test_allow_tarako_payments(self):
        ua = 'Mozilla/5.0 (Mobile; rv:28.1) Gecko/28.1 Firefox 28.1'
        res = self.post(HTTP_USER_AGENT=ua)
        eq_(res.status_code, 200)


class TestSimulatedPayments(PayTester):

    def test_only_simulations(self):
        with self.settings(ONLY_SIMULATIONS=True):
            res = self.post()
            self.assert_error_code(res, msg.PAY_DISABLED, status=503)

    @mock.patch.object(settings, 'ALLOWED_CALLBACK_SCHEMES', ['https'])
    def test_non_https_url_ok_for_simulation(self):
        payjwt = self.payload()
        payjwt['request']['simulate'] = {'result': 'postback'}
        res = self.post(request_kwargs=dict(payload=payjwt))
        eq_(res.status_code, 200)

    def test_configure_simulated_transaction(self):
        simulate = {'result': 'postback'}
        req = self.request(
            payload=self.payload(extra_req={'simulate': simulate}))

        res = self.post(req=req)
        eq_(res.status_code, 200)
        data = json.loads(res.content)
        eq_(data['status'], 'ok')
        eq_(data['simulation'], simulate)

    def test_begin_simulation_when_payments_disabled(self):
        simulate = {'result': 'postback'}
        req = self.request(
            payload=self.payload(extra_req={'simulate': simulate}))

        with self.settings(ONLY_SIMULATIONS=True):
            res = self.post(req=req)
        eq_(res.status_code, 200)
        data = json.loads(res.content)
        eq_(data['simulation'], simulate)

    def test_unknown_simulation(self):
        simulate = {'result': '<script>alert()</script>'}
        req = self.request(
            payload=self.payload(extra_req={'simulate': simulate}))

        res = self.post(req=req)
        self.assert_error_code(res, msg.BAD_SIM_RESULT)

    def test_empty_simulation(self):
        req = self.request(
            payload=self.payload(extra_req={'simulate': {}}))
        res = self.post(req=req)
        eq_(res.status_code, 200, res)

    def test_incomplete_chargeback_simulation(self):
        simulate = {'result': 'chargeback'}
        req = self.request(
            payload=self.payload(extra_req={'simulate': simulate}))

        res = self.post(req=req)
        self.assert_error_code(res, msg.NO_SIM_REASON)

    def test_bad_signature_does_not_store_simulation(self):
        simulate = {'result': 'postback'}
        req = self.request(
            payload=self.payload(extra_req={'simulate': simulate}),
            app_secret=self.secret + '.nope')

        res = self.post(req=req)
        self.assert_error_code(res, msg.INVALID_JWT)

    def test_simulate_disabled_in_settings(self):
        simulate = {'result': 'postback'}
        req = self.request(
            payload=self.payload(extra_req={'simulate': simulate}))

        with self.settings(ALLOW_SIMULATE=False):
            res = self.post(req=req)
        self.assert_error_code(res, msg.SIM_DISABLED)

    @mock.patch('lib.solitude.api.SolitudeAPI.get_active_product')
    def test_issuer_can_only_simulate(self, get_active_product):
        get_active_product.return_value = {'secret': self.secret,
                                           'access': constants.ACCESS_SIMULATE}
        req = self.request(iss='third-party-app')
        # Make a non-simulation request.
        res = self.post(req=req)
        self.assert_error_code(res, msg.SIM_ONLY_KEY)


@mock.patch('webpay.pay.api.client')
class TestGetPay(Base, BaseAPICase):
    def setUp(self):
        super(TestGetPay, self).setUp()
        self.url = reverse('api:pay')
        self.trans_id = 'the-transaction-uuid'
        self.set_session(trans_id=self.trans_id)
        self.transaction_data = {
            'provider': 1,
            'pay_url': 'https://think.this/works?',
        }

    def test_transaction_is_retrieved(self, solitude_client):
        solitude_client.get_transaction.return_value = self.transaction_data
        self.client.get(self.url)
        solitude_client.get_transaction.assert_called_with(uuid=self.trans_id)

    def test_success(self, solitude_client):
        solitude_client.get_transaction.return_value = self.transaction_data
        response = self.client.get(self.url)
        solitude_client.get_transaction.assert_called_with(uuid=self.trans_id)
        eq_(response.status_code, 200)
        eq_(response.data.get('provider'), 'bango')
        eq_(response.data.get('pay_url'), 'https://think.this/works?')

    def test_transaction_not_found(self, solitude_client):
        solitude_client.get_transaction.side_effect = ObjectDoesNotExist
        response = self.client.get(self.url)
        eq_(response.status_code, 404)
        eq_(response.data.get('error_code'), 'TRANSACTION_NOT_FOUND')

    def test_no_trans_id_in_session(self, solitude_client):
        del self.session['trans_id']
        self.save_session()
        response = self.client.get(self.url)
        assert not solitude_client.get_transaction.called
        eq_(response.status_code, 400)
        eq_(response.data.get('error_code'), 'TRANS_ID_NOT_SET')


class TestStartTransactionURL(Base):

    def setUp(self):
        super(TestStartTransactionURL, self).setUp()
        self.start = reverse('api:pay.trans_start_url')

        # Log in.
        self.session['uuid'] = 'verified-user'
        # Start a payment.
        self.session['trans_id'] = 'some:trans'
        self.save_session()

        p = mock.patch('lib.solitude.api.client.get_transaction')
        self.get_transaction = p.start()
        self.addCleanup(p.stop)

    def fake_transaction(self, **kw):
        trans = {
            'status': constants.STATUS_PENDING,
            'uid_pay': 123,
            'pay_url': 'https://bango/pay',
            'provider': constants.PROVIDER_BANGO
        }
        trans.update(kw)
        self.get_transaction.return_value = trans

    def test_no_trans_in_session(self):
        del self.session['trans_id']
        self.save_session()
        res = self.client.get(self.start)
        eq_(res.status_code, 400, res)

    def test_start_ready(self):
        provider = constants.PROVIDER_BANGO
        pay_url = 'https://bango/pay'
        self.fake_transaction(pay_url=pay_url,
                              provider=provider,
                              status=constants.STATUS_PENDING)
        self.session['payment_start'] = time.time()
        self.save_session()
        res = self.client.get(self.start)
        eq_(res.status_code, 200, res.content)
        data = json.loads(res.content)
        eq_(data['url'], pay_url)
        eq_(data['status'], constants.STATUS_PENDING)
        eq_(data['provider'], constants.PROVIDERS_INVERTED[provider])

    def test_start_not_there(self):
        self.get_transaction.side_effect = ObjectDoesNotExist
        res = self.client.get(self.start)
        eq_(res.status_code, 200, res.content)
        data = json.loads(res.content)
        eq_(data['url'], None)
        eq_(data['status'], None)

    def test_start_not_ready(self):
        self.fake_transaction(status=constants.STATUS_RECEIVED)
        res = self.client.get(self.start)
        eq_(res.status_code, 200, res.content)
        data = json.loads(res.content)
        eq_(data['url'], None)
        eq_(data['status'], constants.STATUS_RECEIVED)

    def test_start_errored(self):
        self.fake_transaction(
            status=constants.STATUS_ERRORED,
            status_reason=msg.NO_PUBLICID_IN_JWT
        )
        res = self.client.get(self.start, HTTP_ACCEPT='application/json')
        eq_(res.status_code, 400, res.content)
        data = json.loads(res.content)
        eq_(data['error_code'], msg.NO_PUBLICID_IN_JWT)


class TestPostback(Base):

    def setUp(self):
        super(TestPostback, self).setUp()
        self.callback_success = reverse('api:pay.callback_success_url')
        self.callback_error = reverse('api:pay.callback_error_url')

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
