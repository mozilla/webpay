import base64
import urllib

from django.core.urlresolvers import reverse
from django.conf import settings

import mock
from mock import ANY
from nose.tools import eq_
from pyquery import PyQuery as pq
from slumber.exceptions import HttpClientError
from test_utils import TestCase


from webpay.base.tests import BasicSessionCase


@mock.patch('webpay.bango.views.client.slumber')
@mock.patch('webpay.bango.views.tasks.payment_notify')
class TestBangoReturn(BasicSessionCase):

    def setUp(self):
        super(TestBangoReturn, self).setUp()
        # Log in.
        self.session['uuid'] = 'verified-user'
        # Start a payment.
        self.trans_uuid = 'solitude-trans-uuid'
        self.session['trans_id'] = self.trans_uuid
        self.session['notes'] = {'pay_request': '<request>',
                                 'issuer_key': '<issuer>'}
        self.save_session()

    def call(self, overrides=None, expected_status=200,
             url='bango.success'):
        qs = {'MozSignature': 'xyz',
              'MerchantTransactionId': self.trans_uuid,
              'BillingConfigurationId': '123',
              'ResponseCode': 'OK',
              'Price': '0.99',
              'Currency': 'EUR',
              'BangoTransactionId': '456',
              'Token': '<bango-guid>'}
        if overrides:
            qs.update(overrides)
        res = self.client.get(reverse(url), qs)
        eq_(res.status_code, expected_status)
        return res

    def test_good_return(self, payment_notify, slumber):
        self.call()
        payment_notify.delay.assert_called_with(self.trans_uuid)

    def test_invalid_return(self, payment_notify, slumber):
        err = HttpClientError
        err.content = ''
        slumber.bango.notification.post.side_effect = err
        self.call(expected_status=400)
        assert not payment_notify.delay.called

    def test_transaction_not_in_session(self, payment_notify, slumber):
        del self.session['trans_id']
        self.save_session()

        self.call(overrides={'MerchantTransactionId': 'invalid-trans'},
                  expected_status=200)
        assert slumber.bango.notification.post.called

    def test_transaction_in_session_differs(self, payment_notify, slumber):
        self.call(overrides={'MerchantTransactionId': 'invalid-trans'},
                  expected_status=400)
        assert not slumber.bango.notification.post.called

    def test_error(self, payment_notify, slumber):
        res = self.call(overrides={'ResponseCode': 'NOT OK'},
                        url='bango.error', expected_status=400)
        assert slumber.bango.notification.post.called
        self.assertTemplateUsed(res, 'error.html')

    def test_not_error(self, payment_notify, slumber):
        self.call(overrides={'ResponseCode': 'OK'}, url='bango.error',
                  expected_status=400)

    def test_bad_tier(self, payment_notify, slumber):
        self.call(overrides={'ResponseCode': 'NOT_SUPPORTED'},
                  url='bango.error', expected_status=400)

    def test_not_ok(self, payment_notify, slumber):
        self.call(overrides={'ResponseCode': 'NOT_OK'}, url='bango.success',
                  expected_status=400)

    @mock.patch.object(settings, 'SPA_ENABLE', True)
    def test_success_spa(self, payment_notify, slumber):
        res = self.call()
        doc = pq(res.content)
        eq_(doc('body').attr('data-start-view'), 'payment-success')
        self.assertTemplateUsed('spa/index.html')

    @mock.patch.object(settings, 'SPA_ENABLE', True)
    def test_cancel_spa(self, payment_notify, slumber):
        res = self.call(overrides={'ResponseCode': 'CANCEL'},
                        url='bango.error',
                        expected_status=400)
        doc = pq(res.content)
        eq_(doc('body').attr('data-start-view'), 'payment-failed')
        self.assertTemplateUsed('spa/index.html')

    @mock.patch.object(settings, 'SPA_ENABLE', True)
    def test_error_spa(self, payment_notify, slumber):
        res = self.call(overrides={'ResponseCode': 'NOT_OK'},
                        url='bango.error', expected_status=400)
        doc = pq(res.content)
        eq_(doc('body').attr('data-start-view'), 'payment-failed')
        eq_(doc('body').attr('data-error-code'), 'BANGO_ERROR')
        self.assertTemplateUsed('spa/index.html')


class TestNotification(TestCase):

    def setUp(self):
        self.client = self.client_class()
        self.url = reverse('bango.notification')
        self.auth = 'basic ' + base64.b64encode('u:p')

    def test_get(self):
        eq_(self.client.get(self.url).status_code, 405)

    def test_post_no_auth(self):
        eq_(self.client.post(self.url, data={}).status_code, 401)

    def post(self, **kwargs):
        request = {'data': urllib.urlencode({'XML': '<xml>'}),
                   'content_type': 'application/x-www-form-urlencoded',
                   'HTTP_AUTHORIZATION': self.auth}
        request.update(kwargs)
        return self.client.post(self.url, **request)

    def test_post_incorrect_auth(self):
        res = self.post(HTTP_AUTHORIZATION='foopy')
        eq_(res.status_code, 403)

    @mock.patch('webpay.bango.views.client.slumber')
    def test_post_auth(self, slumber):
        eq_(self.post().status_code, 200)

    @mock.patch('webpay.bango.views.client.slumber')
    def test_post_encoded_auth(self, slumber):
        # This is the first part of a real Bango XML event.
        raw = '\xef\xbb\xbf<?xml version="1.0" encoding="utf-8"?>'
        res = self.post(data=urllib.urlencode({'XML': raw}))
        eq_(slumber.bango.event.post.call_args[0][0]['notification'],
            raw)
        eq_(res.status_code, 200)

    @mock.patch('webpay.bango.views.client.slumber')
    def test_wrong_type(self, slumber):
        eq_(self.post(content_type='text/html').status_code, 415)

    @mock.patch('webpay.bango.views.client.slumber')
    def test_xml(self, slumber):
        xml = '\xef\xbb\xbf<?xml version="1.0" encoding="utf-8"?>'
        res = self.post(data=xml, content_type='text/xml')
        eq_(slumber.bango.event.post.call_args[0][0]['notification'],
            xml)
        eq_(res.status_code, 200)
