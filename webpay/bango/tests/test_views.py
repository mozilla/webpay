from django.core.urlresolvers import reverse

import mock
from nose.tools import eq_
from slumber.exceptions import HttpClientError

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
        self.session.save()

    def call(self, overrides=None, expected_status=200,
             url='bango.success'):
        qs = {'MozSignature': 'xyz',
              'MerchantTransactionId': self.trans_uuid,
              'BillingConfigurationId': '123',
              'ResponseCode': 'OK',
              'BangoTransactionId': '456'}
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
        self.session.save()

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

    def test_not_ok(self, payment_notify, slumber):
        self.call(overrides={'ResponseCode': 'NOT_OK'}, url='bango.success',
                  expected_status=400)
