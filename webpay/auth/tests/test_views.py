import json
from datetime import datetime

from django.conf import settings
from django.core.urlresolvers import reverse

import mock
from nose.tools import eq_

from webpay.base.utils import gmtime
from webpay.base.tests import BasicSessionCase

from . import good_assertion, SessionTestCase


class TestMktPermissions(SessionTestCase):

    def setUp(self):
        super(TestMktPermissions, self).setUp()
        self.url = reverse('auth.verify')
        self.patch('webpay.auth.utils.client.get_buyer')
        self.patch('webpay.auth.views.set_user').return_value = '<user_hash>'
        v = self.patch('webpay.auth.views.BrowserIDBackend')
        v().get_verifier().verify()._response = good_assertion

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
        self.assertCloseToNow(
            datetime.utcfromtimestamp(
                self.client.session['user_reset']['start_ts']))

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

        # User started a PIN reset 15 min ago.
        self.reset_start_ts = gmtime() - (60 * 15)
        # User re-entered auth 5 min after starting a PIN reset.
        self.auth_at = self.reset_start_ts + (60 * 10)

        self._fxa_authorize = self.patch('webpay.auth.views._fxa_authorize')
        self._fxa_authorize.return_value = ({'email': 'fxa@example.com'},
                                            {'auth_at': self.auth_at},)

    def setup_reset(self):
        # This simulates an FxA login after starting a PIN reset.
        self.set_session(user_reset={'start_ts': self.reset_start_ts})

    def patch(self, path):
        p = mock.patch(path)
        self.addCleanup(p.stop)
        return p.start()

    def login(self):
        return self.client.post(
            self.url, {'state': 'some-state', 'auth_response': 'response'})

    def test_successful_login(self):
        response = self.login()
        eq_(response.status_code, 200)
        eq_(json.loads(response.content)['user_email'], 'fxa@example.com')
        eq_(self.client.session['user_reset']['fxa_auth_ts'], self.auth_at)

    def test_successful_login_after_reset(self):
        self.setup_reset()
        response = self.login()
        eq_(response.status_code, 200)

    def test_oauth_error_response(self):
        self._fxa_authorize.return_value = (
            {'code': 400, 'errno': 101, 'error': 'Bad Request',
             'message': 'Unknown client'},
            {'auth_at': self.auth_at},
        )
        response = self.login()
        eq_(response.status_code, 403, response)

    @mock.patch.object(settings, 'USERS_WITH_SUPER_POWERS',
                       ['tom@myspace.com'])
    def test_super_powers(self):
        self._fxa_authorize.return_value = ({'email': 'tom@myspace.com'},
                                            {'auth_at': self.auth_at})
        response = self.login()
        eq_(response.status_code, 200)
        eq_(self.client.session['super_powers'], True)

    def test_no_super_powers_for_nonsuper_users(self):
        response = self.login()
        eq_(response.status_code, 200)
        eq_(self.client.session['super_powers'], False)

    def test_missing_fxa_auth_at(self):
        self._fxa_authorize.return_value = ({'email': 'tom@myspace.com'}, {})
        with self.assertRaises(ValueError):
            self.login()

    def test_invalid_fxa_auth_at(self):
        self._fxa_authorize.return_value = (
            {'email': 'tom@myspace.com'},
            {'auth_at': 'this-is-not-a-number'},
        )
        with self.assertRaises(ValueError):
            self.login()
