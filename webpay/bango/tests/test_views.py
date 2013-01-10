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

    def success(self, overrides=None, expected_status=200):
        qs = {'MozSignature': 'xyz',
              'MerchantTransactionId': self.trans_uuid,
              'BillingConfigurationId': '123',
              'ResponseCode': 'OK',
              'BangoTransactionId': '456'}
        if overrides:
            qs.update(overrides)
        res = self.client.get(reverse('bango.success'), qs)
        eq_(res.status_code, expected_status)
        return res

    def test_good_return(self, payment_notify, slumber):
        self.success()
        payment_notify.delay.assert_called_with(self.trans_uuid)

    def test_invalid_return(self, payment_notify, slumber):
        slumber.bango.payment_notice.post.side_effect = HttpClientError
        self.success(expected_status=400)
        assert not payment_notify.delay.called

    def test_transaction_not_in_session(self, payment_notify, slumber):
        self.success(overrides={'MerchantTransactionId': 'invalid-trans'},
                     expected_status=400)
        assert not payment_notify.delay.called
