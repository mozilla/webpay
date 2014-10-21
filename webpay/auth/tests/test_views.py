import json

from django.conf import settings
from django.core.urlresolvers import reverse

import mock
from nose.tools import eq_

from webpay.auth.utils import get_uuid
from webpay.base.tests import BasicSessionCase

from . import good_assertion, SessionTestCase, set_up_no_mkt_account


@mock.patch.object(settings, 'DOMAIN', 'web.pay')
class TestAuth(SessionTestCase):

    def setUp(self):
        super(TestAuth, self).setUp()
        self.url = reverse('auth.verify')
        self.reverify_url = reverse('auth.reverify')

        get_buyer_patch = mock.patch('webpay.auth.utils.client.get_buyer')
        self.get_buyer = get_buyer_patch.start()
        self.get_buyer.return_value = {'pin': False, 'needs_pin_reset': False}
        self.addCleanup(get_buyer_patch.stop)

        set_up_no_mkt_account(self)

    @mock.patch('webpay.auth.views.verify_assertion')
    @mock.patch('webpay.auth.views.set_user')
    @mock.patch('webpay.auth.views.store_mkt_permissions')
    def test_good_verified(self, store_mkt, set_user_mock, verify_assertion):
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
        assert store_mkt.called, (
            'After login, marketplace permissions should be stored')

    @mock.patch('webpay.auth.views.verify_assertion')
    @mock.patch('webpay.auth.views.set_user')
    def test_good_unverified(self, set_user_mock, verify_assertion):
        set_user_mock.return_value = '<user_hash>'
        verify_assertion.return_value = good_assertion
        res = self.client.post(self.url, {'assertion': 'good'})
        eq_(res.status_code, 200)
        set_user_mock.assert_called_with(mock.ANY, 'a+unverified@a.com')

    @mock.patch('webpay.auth.views.verify_assertion')
    @mock.patch('webpay.auth.utils.client.update_buyer')
    def test_session(self, update_buyer, verify_assertion):
        verify_assertion.return_value = good_assertion
        self.client.post(self.url, {'assertion': 'good'})
        assert self.client.session['uuid'].startswith('web.pay:')

    @mock.patch('webpay.auth.views.verify_assertion')
    @mock.patch('webpay.auth.utils.client.update_buyer')
    def test_session_sets_email(self, update_buyer, verify_assertion):
        verify_assertion.return_value = good_assertion
        self.client.post(self.url, {'assertion': 'good'})
        assert self.client.session['uuid'].startswith('web.pay:')
        update_buyer.assert_called_with(
            self.client.session['uuid'], email='a+unverified@a.com')

    @mock.patch('webpay.auth.views.verify_assertion')
    def test_bad(self, verify_assertion):
        verify_assertion.return_value = False
        eq_(self.client.post(self.url, {'assertion': 'bad'}).status_code, 400)
        eq_(self.client.session.get('was_reverified'), None)

    @mock.patch('webpay.auth.views.verify_assertion')
    def test_session_cleaned(self, verify_assertion):
        self.verify('fake_uuid', 'fake_email')
        verify_assertion.return_value = False
        eq_(self.client.post(self.url, {'assertion': 'bad'}).status_code, 400)
        eq_(self.client.session.get('uuid'), None)

    @mock.patch('webpay.auth.views.verify_assertion')
    @mock.patch('webpay.auth.views.store_mkt_permissions')
    def test_reverify(self, store_mkt, verify_assertion):
        verify_assertion.return_value = dict(good_assertion)
        res = self.client.post(self.reverify_url, {'assertion': 'good'})
        eq_(res.status_code, 200)
        data = json.loads(res.content)
        eq_(data['user_hash'], get_uuid(good_assertion['unverified-email']))
        v = verify_assertion.call_args[0][2]
        assert v['experimental_forceAuthentication'], (
            verify_assertion.call_args)
        eq_(self.client.session['was_reverified'], True)
        assert store_mkt.called, (
            'After reverify, marketplace permissions should be stored')

    @mock.patch('webpay.auth.views.verify_assertion')
    def test_reverify_failed(self, verify_assertion):
        verify_assertion.return_value = dict(good_assertion)
        self.session['uuid'] = 'not-the-same'
        self.save_session()

        res = self.client.post(self.reverify_url, {'assertion': 'good'})
        eq_(res.status_code, 400)


class TestMktPermissions(SessionTestCase):

    def setUp(self):
        super(TestMktPermissions, self).setUp()
        self.url = reverse('auth.verify')
        self.patch('webpay.auth.utils.client.get_buyer')
        self.patch('webpay.auth.views.set_user').return_value = '<user_hash>'
        v = self.patch('webpay.auth.views.verify_assertion')
        v.return_value = good_assertion

        mkt = self.patch('lib.marketplace.api.client.api')
        login = mock.Mock()
        mkt.account.login.return_value = login
        self.account_post = login.post

    def patch(self, path):
        p = mock.patch(path)
        self.addCleanup(p.stop)
        return p.start()

    def verify(self):
        return self.client.post(self.url, {'assertion': 'good'})

    def perms(self):
        perms = {'admin': True, 'reviewer': False}
        self.account_post.return_value = {'permissions': perms,
                                          'settings': {'email': 'a'}}
        return perms

    def test_copy_permissions(self):
        perms = self.perms()
        self.verify()
        eq_(self.client.session['mkt_permissions'], perms)

    @mock.patch.object(settings, 'ALLOW_ADMIN_SIMULATIONS', False)
    def test_no_copy(self):
        self.perms()
        self.verify()
        assert 'mkt_permissions' not in self.client.session


class TestResetUser(BasicSessionCase):

    def test_reset(self):
        uuid = 'some:uuid'
        session = self.client.session
        session['mkt_permissions'] = {'admin': True}
        session['logged_in_user'] = 'jimmy.blazzo@hotmail.com'
        session['uuid'] = uuid
        self.save_session(session)

        self.client.post(reverse('auth.reset_user'))
        eq_(self.client.session.get('logged_in_user'), None)
        eq_(self.client.session.get('uuid'), uuid)
        eq_(self.client.session.get('mkt_permissions'), None)

    def test_when_no_user(self):
        # This should not blow up when no user is in the session.
        self.client.post(reverse('auth.reset_user'))


@mock.patch.object(settings, 'DOMAIN', 'web.pay')
class TestFxALogin(SessionTestCase):

    def setUp(self):
        super(TestFxALogin, self).setUp()
        self.url = reverse('auth.fxa_login')
        self.solitude_client = self.patch('webpay.auth.utils.client')
        self.solitude_client.get_buyer.return_value = {
            'pin': False,
            'needs_pin_reset': False,
        }
        self._fxa_authorize = self.patch('webpay.auth.views._fxa_authorize')
        self._fxa_authorize.return_value = {'email': 'fxa@example.com'}

    def patch(self, path):
        p = mock.patch(path)
        self.addCleanup(p.stop)
        return p.start()

    def login(self):
        return self.client.post(
            self.url, {'state': 'some-state', 'auth_response': 'response'})

    def test_email_is_returned(self):
        response = self.login()
        eq_(response.status_code, 200)
        eq_(json.loads(response.content)['user_email'], 'fxa@example.com')

    def test_was_verified_is_set(self):
        eq_(self.client.session.get('was_reverified'), None)
        response = self.login()
        eq_(response.status_code, 200)
        eq_(self.client.session['was_reverified'], True)
