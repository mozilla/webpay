from django.conf import settings
from django.core.urlresolvers import reverse

import mock
from nose.tools import eq_

from webpay.base import dev_messages as msg
from webpay.base.tests import BasicSessionCase


@mock.patch.object(settings, 'UNIVERSAL_PROVIDER', True)
@mock.patch.object(settings, 'PAYMENT_PROVIDER', 'reference')
class TestProviderSuccess(BasicSessionCase):

    def setUp(self):
        super(TestProviderSuccess, self).setUp()

        # Log in.
        self.session['uuid'] = 'verified-user'
        # Start a payment.
        self.trans_id = 'solitude-trans-uuid'
        self.session['trans_id'] = self.trans_id
        self.session['notes'] = {'pay_request': '<request>',
                                 'issuer_key': '<issuer>'}
        self.save_session()

        # TODO: Add this when verifying tokens. bug 936138
        #p = mock.patch('webpay.provider.views.client.slumber')
        #self.slumber = p.start()
        #self.addCleanup(p.stop)

        p = mock.patch('webpay.provider.views.tasks.payment_notify')
        self.notify = p.start()
        self.addCleanup(p.stop)

    def success(self, data=None, clear_qs=False):
        params = {'ext_transaction_id': self.trans_id}
        if clear_qs:
            params.clear()
        if data:
            params.update(data)
        return self.client.get(reverse('provider.success', args=['reference']),
                               params)

    def test_missing_ext_trans(self):
        res = self.success(clear_qs=True)
        self.assertContains(res, msg.NO_ACTIVE_TRANS,
                            status_code=400)

    def test_missing_session_trans(self):
        del self.session['trans_id']
        self.save_session()
        res = self.success()
        self.assertContains(res, msg.NO_ACTIVE_TRANS,
                            status_code=400)

    def test_success(self):
        res = self.success()
        eq_(res.status_code, 200)
        self.notify.delay.assert_called_with(self.trans_id)
        self.assertTemplateUsed(res, 'provider/success.html')
