import json

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test.utils import override_settings

import mock
from nose.tools import eq_, ok_

from lib.solitude import constants
from lib.solitude.constants import STATUS_PENDING
from webpay.pay.tests import Base, sample

from .base import BaseAPICase


class APIClient(Client):

    def _set(self, **kw):
        kw.setdefault('content_type', 'application/json')
        kw.setdefault('HTTP_ACCEPT', 'application/json')
        return kw

    def get(self, url, data={}, **kw):
        return super(APIClient, self).get(url, data, self._wrap(**kw))

    def post(self, url, data, **kw):
        data = json.dumps(data)
        return super(APIClient, self).get(url, data, self._wrap(**kw))

    def patch(self, url, data, **kw):
        data = json.dumps(data)
        return super(APIClient, self).get(url, data, self._wrap(**kw))


@override_settings(
    KEY='marketplace.mozilla.org', SECRET='marketplace.secret', DEBUG=True,
    ISSUER='marketplace.mozilla.org', INAPP_KEY_PATHS={None: sample})
class TestPay(Base, BaseAPICase):

    def setUp(self):
        super(TestPay, self).setUp()
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

    def post(self, data=None, req=None, mcc='423', mnc='555',
             request_kwargs=None, **kwargs):
        if data is None:
            data = {}
            if req is None:
                req = self.request(**(request_kwargs or {}))
            data = {'req': req, 'mnc': mnc, 'mcc': mcc}
        kwargs.setdefault('HTTP_ACCEPT', 'application/json')
        return self.client.post(self.url, data=data, **kwargs)

    def test_bad(self):
        res = self.post(data={})
        eq_(res.status_code, 400)

    @mock.patch('webpay.pay.tasks.configure_transaction')
    def test_configuration_failure(self, configure):
        configure.return_value = (False, 'FAIL_CODE')
        res = self.post()
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data['error_code'], 'FAIL_CODE')

    def test_inapp(self):
        self.solitude.generic.product.get_object.return_value = {
            'secret': 'p.secret', 'access': constants.ACCESS_PURCHASE}
        res = self.post()
        eq_(res.status_code, 200)
        data = json.loads(res.content)
        eq_(data['status'], 'ok')
        eq_(data['simulation'], None)

    def test_no_mnc_mcc(self):
        res = self.post(mcc='', mnc='')
        eq_(res.status_code, 200)
        args = self.start_pay.delay.call_args[0][1]
        eq_(args['network'], {})

    def test_stores_mnc_mcc(self):
        res = self.post(mnc='423', mcc='555')
        eq_(res.status_code, 200)
        args = self.start_pay.delay.call_args[0][1]
        eq_(args['network'], {'mnc': '423', 'mcc': '555'})

    def test_invalid_mcc(self):
        accept = 'application/json, text/javascript, */*; q=0.01'
        res = self.post(mcc='abc', HTTP_ACCEPT=accept)
        eq_(res.status_code, 400)
        errors = json.loads(res.content)
        ok_('error_code' in errors)

    def test_missing_mcc(self):
        res = self.post(mcc=None)
        eq_(res.status_code, 400)

    def test_configures_transaction_success(self):
        res = self.post()
        eq_(res.status_code, 200)
        data = json.loads(res.content)
        eq_(data['status'], 'ok')
        eq_(data['simulation'], None)

    def test_configure_simulated_transaction(self):
        simulate = {'result': 'postback'}
        req = self.request(
            payload=self.payload(extra_req={'simulate': simulate}))

        res = self.post(req=req)
        eq_(res.status_code, 200)
        data = json.loads(res.content)
        eq_(data['status'], 'ok')
        eq_(data['simulation'], simulate)

    def test_configures_transaction_fail(self):
        res = self.post(req='')  # cause a form error.
        eq_(res.status_code, 400)

    def test_unsupported_jwt_algorithm(self):
        with self.settings(SUPPORTED_JWT_ALGORITHMS=['HS384']):
            res = self.post(
                request_kwargs={'jwt_kwargs': {'algorithm': 'HS256'}})
        eq_(json.loads(res.content)['error_code'], 'INVALID_JWT',
            res.content)
        eq_(res.status_code, 400)

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


@mock.patch('webpay.api.api.client')
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


class TestSimulate(BaseAPICase):

    def setUp(self):
        super(TestSimulate, self).setUp()

        p = mock.patch('webpay.pay.tasks.simulate_notify.delay')
        self.simulate_task = p.start()
        self.addCleanup(p.stop)

        self.issuer = '<issuer>'
        self.pay_request = '<pay request>'

    def activate_simulation(self):
        self.set_session(is_simulation=True,
                         notes={'pay_request': self.pay_request,
                                'issuer_key': self.issuer})

    def test_requires_login(self):
        self.activate_simulation()
        self.client.logout()
        res = self.client.post(reverse('api:simulate'))
        eq_(res.status_code, 403)

    def test_post_required(self):
        res = self.client.get(reverse('api:simulate'))
        eq_(res.status_code, 405)

    def test_no_active_simulation(self):
        res = self.client.post(reverse('api:simulate'))
        eq_(res.status_code, 403, res)

    def test_simulation(self):
        self.activate_simulation()
        res = self.client.post(reverse('api:simulate'))
        eq_(res.status_code, 204)
        self.simulate_task.assert_called_with(self.issuer,
                                              self.pay_request)
