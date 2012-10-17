import calendar
from decimal import Decimal
import json
import time
import urllib2

from django import test
from django.conf import settings

import fudge
from fudge.inspector import arg
import jwt
import mock
from nose.tools import eq_
from requests.exceptions import RequestException, Timeout

from webpay.pay.models import (Issuer, Notice, Transaction,
                               TRANS_STATE_COMPLETED, TRANS_REFUND)
from webpay.pay import tasks
from webpay.pay.samples import JWTtester

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

        app_payment = self.payload()
        self.trans = Transaction.create(
            state=TRANS_STATE_COMPLETED,
            issuer=self.iss,
            issuer_key=self.iss.issuer_key,
            amount=Decimal(app_payment['request']['price'][0]['amount']),
            currency=app_payment['request']['price'][0]['currency'],
            name=app_payment['request']['name'],
            description=app_payment['request']['description'],
            json_request=json.dumps(app_payment))

    def iss_update(self, **kw):
        Issuer.objects.filter(pk=self.iss.pk).update(**kw)

    def do_chargeback(self, reason):
        self.trans.typ = TRANS_REFUND
        self.trans.save()
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            tasks.chargeback_notify(self.trans.pk, reason)

    def notify(self):
        with self.settings(INAPP_KEY_PATHS={None: sample}, DEBUG=True):
            tasks.payment_notify(self.trans.pk)

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
                                 .has_attr(text=str(self.trans.pk))
                                 .expects('raise_for_status'))
        self.notify()
        notice = Notice.objects.get()
        eq_(notice.transaction.pk, self.trans.pk)
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
            eq_(dd['response']['transactionID'], self.trans.pk)
            eq_(dd['response']['reason'], 'refund')
            jwt.decode(req, self.iss.get_private_key(), verify=True)
            return True

        (fake_req.expects('post').with_args(url, arg.passes_test(req_ok),
                                            timeout=5)
                                 .returns_fake()
                                 .has_attr(text=str(self.trans.pk))
                                 .expects('raise_for_status'))
        self.do_chargeback('refund')
        notice = Notice.objects.get()
        eq_(notice.transaction.pk, self.trans.pk)
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
                                 .has_attr(text=str(self.trans.pk))
                                 .expects('raise_for_status'))
        self.do_chargeback('reversal')
        notice = Notice.objects.get()
        eq_(notice.transaction.pk, self.trans.pk)
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
            eq_(data['request']['price'][0]['amount'],
                app_payment['request']['price'][0]['amount'])
            eq_(data['request']['price'][0]['currency'],
                app_payment['request']['price'][0]['currency'])
            eq_(data['request']['name'], app_payment['request']['name'])
            eq_(data['request']['description'],
                app_payment['request']['description'])
            eq_(data['request']['productdata'],
                app_payment['request']['productdata'])
            eq_(data['response']['transactionID'], self.trans.pk)
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
