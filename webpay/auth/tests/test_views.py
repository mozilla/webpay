import json

from django.conf import settings
from django.core.urlresolvers import reverse

import mock
from nose.tools import eq_

from webpay.auth.utils import get_uuid, client
from webpay.base.tests import BasicSessionCase

from . import good_assertion, SessionTestCase


@mock.patch.object(client, 'get_buyer',
                   lambda *args: {'pin': False, 'needs_pin_reset': False})
@mock.patch.object(settings, 'DOMAIN', 'web.pay')
class TestAuth(SessionTestCase):

    def setUp(self):
        super(TestAuth, self).setUp()
        self.url = reverse('auth.verify')
        self.reverify_url = reverse('auth.reverify')
        patch = mock.patch('webpay.auth.views.pay_tasks.configure_transaction')
        self.config_trans = patch.start()
        self.patches = [patch]

    def tearDown(self):
        super(TestAuth, self).tearDown()
        for p in self.patches:
            p.stop()

    @mock.patch('webpay.auth.views.verify_assertion')
    @mock.patch('webpay.auth.views.set_user')
    def test_good_verified(self, set_user_mock, verify_assertion):
        set_user_mock.return_value = '<user_hash>'
        assertion = dict(good_assertion)
        del assertion['unverified-email']
        assertion['email'] = 'a@a.com'
        verify_assertion.return_value = assertion
        res = self.client.post(self.url, {'assertion': 'good'})
        eq_(res.status_code, 200)
        data = json.loads(res.content)
        eq_(data['user_hash'], '<user_hash>')
        set_user_mock.assert_called_with(mock.ANY, 'a@a.com')
        assert self.config_trans.called, (
                'After login, transaction should be configured in background')

    @mock.patch('webpay.auth.views.verify_assertion')
    @mock.patch('webpay.auth.views.set_user')
    def test_good_unverified(self, set_user_mock, verify_assertion):
        set_user_mock.return_value = '<user_hash>'
        verify_assertion.return_value = good_assertion
        res = self.client.post(self.url, {'assertion': 'good'})
        eq_(res.status_code, 200)
        set_user_mock.assert_called_with(mock.ANY, 'a+unverified@a.com')

    @mock.patch('webpay.auth.views.verify_assertion')
    def test_session(self, verify_assertion):
        verify_assertion.return_value = good_assertion
        self.client.post(self.url, {'assertion': 'good'})
        assert self.client.session['uuid'].startswith('web.pay:')

    @mock.patch('webpay.auth.views.verify_assertion')
    def test_bad(self, verify_assertion):
        verify_assertion.return_value = False
        eq_(self.client.post(self.url, {'assertion': 'bad'}).status_code, 400)

    @mock.patch('webpay.auth.views.verify_assertion')
    def test_session_cleaned(self, verify_assertion):
        self.verify('a:b')
        verify_assertion.return_value = False
        eq_(self.client.post(self.url, {'assertion': 'bad'}).status_code, 400)
        eq_(self.client.session.get('uuid'), None)

    @mock.patch('webpay.auth.views.verify_assertion')
    def test_reverify(self, verify_assertion):
        verify_assertion.return_value = dict(good_assertion)
        res = self.client.post(self.reverify_url, {'assertion': 'good'})
        eq_(res.status_code, 200)
        data = json.loads(res.content)
        eq_(data['user_hash'], get_uuid(good_assertion['unverified-email']))
        v = verify_assertion.call_args[0][2]
        assert v['experimental_forceAuthentication'], (
            verify_assertion.call_args)


class TestResetUser(BasicSessionCase):

    def test_reset(self):
        uuid = 'some:uuid'
        session = self.client.session
        session['logged_in_user'] = 'jimmy.blazzo@hotmail.com'
        session['uuid'] = uuid
        session.save()
        self.client.post(reverse('auth.reset_user'))
        eq_(self.client.session.get('logged_in_user'), None)
        eq_(self.client.session.get('uuid'), uuid)

    def test_when_no_user(self):
        # This should not blow up when no user is in the session.
        self.client.post(reverse('auth.reset_user'))
