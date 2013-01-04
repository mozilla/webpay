import calendar
import time
import urllib2

from django import test
from django.conf import settings

import fudge
from fudge.inspector import arg
import jwt
import mock
from nose.exc import SkipTest
from nose.tools import eq_, raises
from requests.exceptions import RequestException, Timeout
import test_utils


from lib.marketplace.api import TierNotFound
from lib.solitude import api
from lib.solitude import constants
from webpay.pay import tasks
from webpay.pay.models import Issuer, Notice
from webpay.pay.samples import JWTtester
from webpay.pay.tasks import get_effective_issuer_key

from .test_views import sample


class TestNotifyApp(JWTtester, test.TestCase):

    def url(self, path, protocol='https'):
        return protocol + '://' + self.domain + path

    def setUp(self):
        super(TestNotifyApp, self).setUp()
        self.domain = 'somenonexistantappdomain.com'
        self.inapp_key = '1234'
        self.inapp_secret = 'politics is just lies, smoke, and mirrors'
        self.postback = '/postback'
        self.chargeback = '/chargeback'
        self.iss = Issuer.objects.create(domain=self.domain,
                                         issuer_key=self.inapp_key,
                                         postback_url=self.postback,
                                         chargeback_url=self.chargeback)
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            self.iss.set_private_key(self.inapp_secret)

        self.trans_uuid = 'some:uuid'

    def iss_update(self, **kw):
        Issuer.objects.filter(pk=self.iss.pk).update(**kw)

    @mock.patch('lib.solitude.api.client.get_transaction')
    def do_chargeback(self, reason, get_transaction):
        get_transaction.return_value = {
                'status': constants.STATUS_COMPLETED,
                'notes': {'pay_request': self.payload(),
                          'issuer_key': self.iss.issuer_key,
                          'issuer': Issuer.objects.get(pk=self.iss.pk)},
                'type': constants.TYPE_REFUND,
                'uuid': self.trans_uuid
        }
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            tasks.chargeback_notify(self.trans_uuid, reason)

    @mock.patch('lib.solitude.api.client.get_transaction')
    def notify(self, get_transaction):
        get_transaction.return_value = {
                'status': constants.STATUS_COMPLETED,
                'notes': {'pay_request': self.payload(),
                          'issuer_key': self.iss.issuer_key,
                          'issuer': Issuer.objects.get(pk=self.iss.pk)},
                'type': constants.TYPE_PAYMENT,
                'uuid': self.trans_uuid
        }
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            tasks.payment_notify('some:uuid')

    @fudge.patch('webpay.pay.utils.requests')
    def test_notify_pay(self, fake_req):
        url = self.url(self.postback)
        payload = self.payload(typ='mozilla/payments/pay/postback/v1')

        def req_ok(req):
            dd = jwt.decode(req, verify=False)
            eq_(dd['request'], payload['request'])
            eq_(dd['typ'], payload['typ'])
            jwt.decode(req, self.iss.get_private_key(), verify=True)
            return True

        (fake_req.expects('post').with_args(url, arg.passes_test(req_ok),
                                            timeout=5)
                                 .returns_fake()
                                 .has_attr(text=self.trans_uuid)
                                 .expects('raise_for_status'))
        self.notify()
        notice = Notice.objects.get()
        eq_(notice.transaction_uuid, self.trans_uuid)
        eq_(notice.success, True)
        eq_(notice.url, url)

    @fudge.patch('webpay.pay.utils.requests')
    def test_notify_refund_chargeback(self, fake_req):
        url = self.url(self.chargeback)
        payload = self.payload(typ='mozilla/payments/pay/chargeback/v1')

        def req_ok(req):
            dd = jwt.decode(req, verify=False)
            eq_(dd['request'], payload['request'])
            eq_(dd['typ'], payload['typ'])
            eq_(dd['response']['transactionID'], self.trans_uuid)
            eq_(dd['response']['reason'], 'refund')
            jwt.decode(req, self.iss.get_private_key(), verify=True)
            return True

        (fake_req.expects('post').with_args(url, arg.passes_test(req_ok),
                                            timeout=5)
                                 .returns_fake()
                                 .has_attr(text=self.trans_uuid)
                                 .expects('raise_for_status'))
        self.do_chargeback('refund')
        notice = Notice.objects.get()
        eq_(notice.transaction_uuid, self.trans_uuid)
        eq_(notice.success, True)
        eq_(notice.url, url)

    @fudge.patch('webpay.pay.utils.requests')
    def test_notify_reversal_chargeback(self, fake_req):
        url = self.url(self.chargeback)

        def req_ok(req):
            dd = jwt.decode(req, verify=False)
            eq_(dd['response']['reason'], 'reversal')
            return True

        (fake_req.expects('post').with_args(url, arg.passes_test(req_ok),
                                            timeout=5)
                                 .returns_fake()
                                 .has_attr(text=self.trans_uuid)
                                 .expects('raise_for_status'))
        self.do_chargeback('reversal')
        notice = Notice.objects.get()
        eq_(notice.transaction_uuid, self.trans_uuid)
        eq_(notice.last_error, '')
        eq_(notice.success, True)

    @mock.patch.object(settings, 'INAPP_REQUIRE_HTTPS', True)
    @fudge.patch('webpay.pay.utils.requests')
    def test_force_https(self, fake_req):
        self.iss_update(is_https=False)
        url = self.url(self.postback, protocol='https')
        (fake_req.expects('post').with_args(url, arg.any(), timeout=arg.any())
                                 .returns_fake()
                                 .is_a_stub())
        self.notify()
        notice = Notice.objects.get()
        eq_(notice.last_error, '')

    @mock.patch.object(settings, 'INAPP_REQUIRE_HTTPS', False)
    @fudge.patch('webpay.pay.utils.requests')
    def test_configurable_https(self, fake_req):
        self.iss_update(is_https=True)
        url = self.url(self.postback, protocol='https')
        (fake_req.expects('post').with_args(url, arg.any(), timeout=arg.any())
                                 .returns_fake()
                                 .is_a_stub())
        self.notify()
        notice = Notice.objects.get()
        eq_(notice.last_error, '')

    @mock.patch.object(settings, 'INAPP_REQUIRE_HTTPS', False)
    @fudge.patch('webpay.pay.utils.requests')
    def test_configurable_http(self, fake_req):
        self.iss_update(is_https=False)
        url = self.url(self.postback, protocol='http')
        (fake_req.expects('post').with_args(url, arg.any(), timeout=arg.any())
                                 .returns_fake()
                                 .is_a_stub())
        self.notify()
        notice = Notice.objects.get()
        eq_(notice.last_error, '')

    @fudge.patch('webpay.pay.utils.requests')
    def test_notify_timeout(self, fake_req):
        fake_req.expects('post').raises(Timeout())
        self.notify()
        notice = Notice.objects.get()
        eq_(notice.success, False)
        er = notice.last_error
        assert er.startswith('Timeout:'), 'Unexpected: %s' % er

    @mock.patch('webpay.pay.tasks.payment_notify.retry')
    @mock.patch('webpay.pay.utils.requests.post')
    def test_retry_http_error(self, post, retry):
        post.side_effect = RequestException('500 error')
        self.notify()
        assert post.called, 'notification not sent'
        assert retry.called, 'task was not retried after error'

    @fudge.patch('webpay.pay.utils.requests')
    def test_any_error(self, fake_req):
        fake_req.expects('post').raises(RequestException('some http error'))
        self.notify()
        notice = Notice.objects.get()
        eq_(notice.success, False)
        er = notice.last_error
        assert er.startswith('RequestException:'), 'Unexpected: %s' % er

    @fudge.patch('webpay.pay.utils.requests')
    def test_bad_status(self, fake_req):
        (fake_req.expects('post').returns_fake()
                                 .has_attr(text='')
                                 .expects('raise_for_status')
                                 .raises(urllib2.HTTPError('url', 500, 'Error',
                                                           [], None)))
        self.notify()
        notice = Notice.objects.get()
        eq_(notice.success, False)
        er = notice.last_error
        assert er.startswith('HTTPError:'), 'Unexpected: %s' % er

    @fudge.patch('webpay.pay.utils.requests')
    def test_invalid_app_response(self, fake_req):
        (fake_req.expects('post').returns_fake()
                                 .provides('raise_for_status')
                                 .has_attr(text='<not a valid response>'))
        self.notify()
        notice = Notice.objects.get()
        eq_(notice.success, False)

    @fudge.patch('webpay.pay.utils.requests')
    def test_signed_app_response(self, fake_req):
        app_payment = self.payload()

        # Ensure that the JWT sent to the app for payment notification
        # includes the same payment data that the app originally sent.
        def is_valid(payload):
            data = jwt.decode(payload, self.iss.get_private_key(),
                              verify=True)
            eq_(data['iss'], settings.NOTIFY_ISSUER)
            eq_(data['aud'], self.iss.issuer_key)
            eq_(data['typ'], 'mozilla/payments/pay/postback/v1')
            eq_(data['request']['pricePoint'], 1)
            eq_(data['request']['name'], app_payment['request']['name'])
            eq_(data['request']['description'],
                app_payment['request']['description'])
            eq_(data['request']['productdata'],
                app_payment['request']['productdata'])
            eq_(data['response']['transactionID'], 'some:uuid')
            assert data['iat'] <= calendar.timegm(time.gmtime()) + 60, (
                                'Expected iat to be about now')
            assert data['exp'] > calendar.timegm(time.gmtime()) + 3500, (
                                'Expected exp to be about an hour from now')
            return True

        (fake_req.expects('post').with_args(arg.any(),
                                            arg.passes_test(is_valid),
                                            timeout=arg.any())
                                 .returns_fake()
                                 .has_attr(text='<not a valid response>')
                                 .provides('raise_for_status'))
        self.notify()


class TestStartPay(test_utils.TestCase):

    def setUp(self):
        self.issue = 'some-seller-uuid'
        self.transaction_uuid = 'webpay:some-id'
        self.notes = {'issuer': None,
                      'issuer_key': self.issue,
                      'pay_request': {
                            'iss': 'some-seller-key',
                            'request': {'pricePoint': 1,
                                        'id': 'generated-product-uuid',
                                        'name': 'Virtual Sword'}}}
        self.prices = {'prices': [{'amount': 1, 'currency': 'EUR'}]}

    @mock.patch('lib.solitude.api.client.get_transaction')
    def start(self, solitude):
        solitude.get_transaction.return_value = {
                'status': constants.STATUS_COMPLETED,
                'notes': self.notes,
                'type': constants.TYPE_PAYMENT,
                'uuid': self.transaction_uuid
        }
        tasks.start_pay(self.transaction_uuid, self.notes)

    def set_billing_id(self, slumber, num):
        slumber.bango.billing.post.return_value = {
            'resource_pk': '3333',
            'billingConfigurationId': num,
            'responseMessage': 'Success',
            'responseCode': 'OK',
            'resource_uri': '/bango/billing/3333/'
        }

    @raises(api.SellerNotConfigured)
    @mock.patch('lib.solitude.api.client.slumber')
    @mock.patch('lib.marketplace.api.client.slumber')
    def test_no_seller(self, marketplace, solitude):
        raise SkipTest
        marketplace.webpay.prices.return_value = self.prices
        solitude.generic.seller.get.return_value = {'meta': {'total_count': 0}}
        self.start()
        #eq_(self.get_trans().status, TRANS_STATE_FAILED)

    @mock.patch('lib.solitude.api.client.slumber')
    @mock.patch('lib.marketplace.api.client.slumber')
    def test_existing_product(self, marketplace, solitude):
        marketplace.webpay.prices.return_value = self.prices
        solitude.generic.seller.get.return_value = {
            'meta': {'total_count': 1},
            'objects': [{
                'resource_pk': 29,
                'uuid': self.issue,
            }]
        }
        solitude.bango.product.get.return_value = {
            'meta': {'total_count': 1},
            'objects': [{
                'resource_pk': 15,
                'bango_id': u'1113330000000311563',
                'seller_product': u'/generic/product/20/',
                'resource_uri': '/bango/product/15/'
            }]
        }
        self.set_billing_id(solitude, 123)
        self.start()
        assert solitude.generic.transaction.called

    @mock.patch('lib.solitude.api.client.slumber')
    @mock.patch('lib.marketplace.api.client.slumber')
    def test_price_used(self, marketplace, solitude):
        prices = mock.Mock()
        prices.get.return_value = self.prices
        marketplace.api.webpay.prices.return_value = prices
        self.set_billing_id(solitude, 123)
        self.start()
        eq_(solitude.bango.billing.post.call_args[0][0]['prices'],
            self.prices['prices'])

    @mock.patch('lib.solitude.api.client.slumber')
    @mock.patch('lib.marketplace.api.client.slumber')
    def test_price_fails(self, marketplace, solitude):
        marketplace.api.webpay.prices.side_effect = TierNotFound
        with self.assertRaises(TierNotFound):
            self.start()

    @mock.patch('lib.solitude.api.client.slumber')
    @mock.patch('lib.marketplace.api.client.slumber')
    @raises(RuntimeError)
    def test_exception_fails_transaction(self, marketplace, slumber):
        raise SkipTest
        slumber.generic.seller.get.side_effect = RuntimeError
        self.start()
        #trans = self.get_trans()
        # Currently solitude doesn't have the concept of a failed transaction.
        # Perhaps we should add that?
        #eq_(trans.status, TRANS_STATE_FAILED)

    @mock.patch.object(settings, 'KEY', 'marketplace-domain')
    @mock.patch('lib.solitude.api.client.slumber')
    @mock.patch('lib.marketplace.api.client.slumber')
    def test_marketplace_seller_switch(self, marketplace, solitude):
        marketplace.webpay.prices.return_value = self.prices
        self.set_billing_id(solitude, 123)

        # Simulate how the Marketplace would add
        # a custom seller_uuid to the product data in the JWT.
        app_seller_uuid = 'some-seller-uuid'
        data = 'seller_uuid=%s' % app_seller_uuid
        self.notes['pay_request']['iss'] = 'marketplace-domain'
        self.notes['pay_request']['request']['productData'] = data
        self.start()

        # Check that the seller_uuid was switched to that of the app seller.
        solitude.generic.seller.get.assert_called_with(
            uuid=app_seller_uuid)

    @raises(ValueError)
    @mock.patch.object(settings, 'KEY', 'marketplace-domain')
    @mock.patch('lib.solitude.api.client.slumber')
    def test_marketplace_missing_seller_uuid(self, slumber):
        self.notes['issuer_key'] = settings.KEY
        self.notes['pay_request']['request']['productData'] = 'foo-bar'
        self.start()

    def test_get_effective_issuer(self):
        iss = Issuer()
        eq_(get_effective_issuer_key(iss, 'foo'), 'foo')
        iss.issuer_key = 'bar'
        eq_(get_effective_issuer_key(iss, 'foo'), 'bar')
        eq_(get_effective_issuer_key(None, 'foo'), 'foo')
