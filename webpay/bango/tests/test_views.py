import base64

from django.core.urlresolvers import reverse

import mock
from mock import ANY
from nose.tools import eq_
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

    def test_cancel(self, payment_notify, slumber):
        res = self.call(overrides={'ResponseCode': 'CANCEL'},
                        url='bango.error',
                        expected_status=200)
        self.assertTemplateUsed(res, 'bango/cancel.html')

    def test_not_error(self, payment_notify, slumber):
        self.call(overrides={'ResponseCode': 'OK'}, url='bango.error',
                  expected_status=400)

    def test_bad_tier(self, payment_notify, slumber):
        self.call(overrides={'ResponseCode': 'NOT_SUPPORTED'},
                  url='bango.error', expected_status=400)

    def test_not_ok(self, payment_notify, slumber):
        self.call(overrides={'ResponseCode': 'NOT_OK'}, url='bango.success',
                  expected_status=400)

    @mock.patch('webpay.bango.views.tasks.fake_payment_notify')
    def test_fake_notice(self, fake_notify, pay_notify, slumber):
        with self.settings(FAKE_PAYMENTS=True):
            self.call()
        fake_notify.delay.assert_called_with(ANY, '<request>', '<issuer>')
        assert not pay_notify.called


class TestNotification(TestCase):

    def setUp(self):
        self.client = self.client_class()
        self.url = reverse('bango.notification')
        self.auth = 'basic ' + base64.b64encode('u:p')

    def test_get(self):
        eq_(self.client.get(self.url).status_code, 405)

    def test_post_no_auth(self):
        eq_(self.client.post(self.url, data={}).status_code, 401)

    def test_post_incorrect_auth(self):
        res = self.client.post(self.url, data={'XML': '<xml>'},
                               HTTP_AUTHORIZATION='foopy')
        eq_(res.status_code, 403)

    @mock.patch('webpay.bango.views.client.slumber')
    def test_post_auth(self, slumber):
        res = self.client.post(self.url, data={'XML': '<xml>'},
                               HTTP_AUTHORIZATION=self.auth)
        eq_(slumber.bango.event.post.call_args[0][0]['notification'],
            '<xml>')
        eq_(res.status_code, 200)

    @mock.patch('webpay.bango.views.client.slumber')
    def test_post_encoded_auth(self, slumber):
        # This is the first part of a real Bango XML event.
        raw = '\xef\xbb\xbf<?xml version="1.0" encoding="utf-8"?>'
        # A real Bango request seems to not specify content-type but
        # that's hard to simulate in Django.
        res = self.client.post(self.url, data={'XML': raw},
                               HTTP_AUTHORIZATION=self.auth)
        eq_(slumber.bango.event.post.call_args[0][0]['notification'],
            raw)
        eq_(res.status_code, 200)
