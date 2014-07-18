import json

from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test.utils import override_settings

import mock
from curling.lib import HttpClientError
from nose import SkipTest
from nose.tools import eq_, ok_

from lib.marketplace.api import client as marketplace
from lib.solitude import constants
from lib.solitude.api import client as solitude
from lib.solitude.constants import STATUS_PENDING
from webpay.base.tests import BasicSessionCase
from webpay.pay.tests import Base, sample


class Response():

    def __init__(self, code, content=''):
        self.status_code = code
        self.content = content


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


class BaseCase(BasicSessionCase):

    def setUp(self, *args, **kw):
        super(BaseCase, self).setUp(*args, **kw)
        self.uuid = 'fake-uuid'
        self.email = 'fake@user.com'
        self.set_session(uuid=self.uuid)
        self.set_session(logged_in_user=self.email)

        p = mock.patch.object(solitude, 'slumber', name='patched:solitude')
        self.solitude = p.start()
        self.addCleanup(p.stop)

        m = mock.patch.object(marketplace, 'api', name='patched:market')
        prices = mock.Mock()
        prices.get_object.return_value = 1
        self.marketplace = m.start()
        self.marketplace.webpay.prices.return_value = prices
        self.addCleanup(m.stop)

    def set_session(self, **kwargs):
        self.session.update(kwargs)
        self.save_session()

    def error(self, status):
        error = HttpClientError
        error.response = Response(404)
        return error


class PIN(BaseCase):

    def setUp(self, *args, **kw):
        super(PIN, self).setUp(*args, **kw)
        self.url = reverse('api:pin')


class TestError(PIN):

    def test_error(self):
        # A test that the API returns JSON.
        res = self.client.post(self.url, {}, HTTP_ACCEPT='application/json')
        eq_(res.status_code, 400)
        ok_('error_code', json.loads(res.content))


class TestGet(PIN):

    def test_anon(self):
        self.set_session(uuid=None)
        eq_(self.client.get(self.url).status_code, 403)

    def test_no_pin(self):
        self.solitude.generic.buyer.get_object_or_404.side_effect = (
            ObjectDoesNotExist)
        res = self.client.get(self.url)
        eq_(res.status_code, 200)
        eq_(json.loads(res.content)['pin'], False)

    def test_some_pin(self):
        self.solitude.generic.buyer.get_object_or_404.return_value = {
            'pin': True}
        res = self.client.get(self.url)
        self.solitude.generic.buyer.get_object_or_404.assert_called_with(
            headers={}, uuid=self.uuid)
        eq_(json.loads(res.content)['pin'], True)

    def test_user_not_reverified(self):
        self.solitude.generic.buyer.get_object_or_404.return_value = {
            'pin': True}
        res = self.client.get(self.url)
        eq_(json.loads(res.content)['pin_reset_started'], False)

    def test_user_was_reverified(self):
        self.solitude.generic.buyer.get_object_or_404.return_value = {
            'pin': True}
        self.session.update({'was_reverified': True})
        self.save_session()
        res = self.client.get(self.url)
        eq_(json.loads(res.content)['pin_reset_started'], True)


class TestPost(PIN):

    def test_anon(self):
        self.set_session(uuid=None)
        eq_(self.client.post(self.url, {}).status_code, 403)

    def test_no_data(self):
        res = self.client.post(self.url, {})
        eq_(res.status_code, 400)

    @mock.patch('webpay.api.api.client')
    def test_user(self, solitude_client):
        self.solitude.generic.buyer.get_object_or_404.return_value = {
            'pin': False, 'resource_pk': 'abc'}
        res = self.client.post(self.url, {'pin': '1234'})
        eq_(res.status_code, 204)
        solitude_client.change_pin.assert_called_with(
            self.uuid, '1234', etag='', pin_confirmed=True,
            clear_was_locked=True)

    def test_user_with_pin(self):
        self.solitude.generic.buyer.get_object_or_404.return_value = {
            'pin': True, 'resource_pk': 'abc'}
        res = self.client.post(self.url, {'pin': '1234'})
        eq_(res.status_code, 400)


class TestPatch(PIN):

    def setUp(self):
        super(TestPatch, self).setUp()
        self.uuid = '1120933'
        self.set_session(was_reverified=True, uuid=self.uuid)
        solitude_client_patcher = mock.patch('webpay.api.api.client')
        self.solitude_client = solitude_client_patcher.start()
        self.addCleanup(solitude_client_patcher.stop)

    def patch(self, url, data=None):
        """
        A wrapper around self.client.generic until we upgrade Django
        and get the patch method in the test client.
        """
        data = data or {}
        return self.client.generic('PATCH', url, data=json.dumps(data),
                                   content_type='application/json')

    def test_anon(self):
        self.set_session(uuid=None)
        eq_(self.patch(self.url, {}).status_code, 403)

    def test_no_data(self):
        res = self.patch(self.url, data={})
        eq_(res.status_code, 400)

    def test_no_user(self):
        # TODO: it looks like the PIN flows doesn't take this into account.
        raise SkipTest

    def test_not_reverified(self):
        self.set_session(was_reverified=False)
        res = self.patch(self.url, data={})
        eq_(res.status_code, 400)

    def test_change(self):
        self.solitude_client.change_pin.return_value = {}
        res = self.patch(self.url, data={'pin': '1234'})
        eq_(res.status_code, 204)
        self.solitude_client.change_pin.assert_called_with(
            self.uuid, '1234', pin_confirmed=True, clear_was_locked=True)

    def test_reverified(self):
        self.solitude_client.change_pin.return_value = {}
        assert self.client.session['was_reverified']
        res = self.patch(self.url, data={'pin': '1234'})
        eq_(res.status_code, 204)
        assert not self.client.session['was_reverified']


class TestCheck(PIN):

    def setUp(self):
        super(TestCheck, self).setUp()
        self.url = reverse('api:pin.check')

    def test_anon(self):
        self.set_session(uuid=None)
        eq_(self.client.post(self.url).status_code, 403)

    def test_no_data(self):
        res = self.client.post(self.url, data={})
        eq_(res.status_code, 400)

    def test_good(self):
        self.solitude.generic.verify_pin.post.return_value = {'valid': True}
        res = self.client.post(self.url, data={'pin': 1234})
        eq_(res.status_code, 200)

    def test_locked(self):
        self.solitude.generic.verify_pin.post.return_value = {'locked': True}
        res = self.client.post(self.url, data={'pin': 1234})
        eq_(res.status_code, 400)

    def test_wrong(self):
        self.solitude.generic.verify_pin.post.return_value = {'valid': False}
        self.solitude.generic.buyer.get_object_or_404.return_value = {
            'pin': True, 'resource_pk': 'abc'}
        res = self.client.post(self.url, data={'pin': 1234})
        eq_(res.status_code, 400)

    def test_404(self):
        self.solitude.generic.verify_pin.post.side_effect = (
            ObjectDoesNotExist)
        res = self.client.post(self.url, data={'pin': 1234})
        eq_(res.status_code, 404)

    def test_output(self):
        self.solitude.generic.verify_pin.post.return_value = {'valid': False}
        self.solitude.generic.buyer.get_object_or_404.return_value = {
            'pin': True, 'resource_pk': 'abc'}
        res = self.client.post(self.url, data={'pin': 1234})
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data, {'pin': True,
                   'pin_locked_out': None,
                   'pin_is_locked_out': None,
                   'pin_was_locked_out': None,
                   'pin_reset_started': None})


@override_settings(
    KEY='marketplace.mozilla.org', SECRET='marketplace.secret', DEBUG=True,
    ISSUER='marketplace.mozilla.org', INAPP_KEY_PATHS={None: sample})
class TestPay(Base, BaseCase):

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

    def post(self, data=None, req=None, mcc='423', mnc='555', **kwargs):
        if data is None:
            data = {}
            if req is None:
                req = self.request()
            data = {'req': req, 'mnc': mnc, 'mcc': mcc}
        return self.client.post(self.url, data=data, **kwargs)

    def test_bad(self):
        res = self.post(data={})
        eq_(res.status_code, 400)

    def test_inapp(self):
        self.solitude.generic.product.get_object.return_value = {
            'secret': 'p.secret', 'access': constants.ACCESS_PURCHASE}
        res = self.post()
        eq_(res.status_code, 204)

    def test_no_mnc_mcc(self):
        res = self.post(mcc='', mnc='')
        eq_(res.status_code, 204)
        args = self.start_pay.delay.call_args[0][1]
        eq_(args['network'], {})

    def test_stores_mnc_mcc(self):
        res = self.post(mnc='423', mcc='555')
        eq_(res.status_code, 204)
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
        eq_(res.status_code, 204)

    def test_configures_transaction_fail(self):
        res = self.post(req='')  # cause a form error.
        eq_(res.status_code, 400)


@mock.patch('webpay.api.api.client')
class TestGetPay(Base, BaseCase):
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
