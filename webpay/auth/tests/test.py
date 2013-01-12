import json

from django import test
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpRequest
from django.utils.importlib import import_module

import mock
from nose.tools import eq_

from webpay.auth.utils import client
from webpay.auth import views as auth_views


good_assertion = {u'status': u'okay',
                  u'audience': u'http://some.site',
                  u'expires': 1351707833170,
                  u'unverified-email': u'a+unverified@a.com',
                  u'issuer': u'login.persona.org'}


class SessionTestCase(test.TestCase):
    """
    A wrapper around Django tests to provide a verify method for use
    in testing.
    """

    def verify(self, uuid):
        # This is a rip off of the Django test client login.
        engine = import_module(settings.SESSION_ENGINE)

        # Create a fake request to store login details.
        request = HttpRequest()
        request.session = engine.SessionStore()

        request.session['uuid'] = uuid
        request.session.save()

        # Set the cookie to represent the session.
        session_cookie = settings.SESSION_COOKIE_NAME
        self.client.cookies[session_cookie] = request.session.session_key
        cookie_data = {
                'max-age': None,
                'path': '/',
                'domain': settings.SESSION_COOKIE_DOMAIN,
                'secure': settings.SESSION_COOKIE_SECURE or None,
                'expires': None,
        }
        self.client.cookies[session_cookie].update(cookie_data)
        self.request = request

    def unverify(self):
        # Remove the browserid verification.
        del self.client.cookies[settings.SESSION_COOKIE_NAME]


@mock.patch.object(client, 'get_buyer',
                   lambda *args: {'pin': False, 'needs_pin_reset': False})
@mock.patch.object(settings, 'DOMAIN', 'web.pay')
class TestAuth(SessionTestCase):

    def setUp(self):
        self.url = reverse('auth.verify')

    @mock.patch('webpay.auth.views.verify_assertion')
    @mock.patch('webpay.auth.views.set_user')
    def test_good_verified(self, set_user_mock, verify_assertion):
        assertion = dict(good_assertion)
        del assertion['unverified-email']
        assertion['email'] = 'a@a.com'
        verify_assertion.return_value = assertion
        res = self.client.post(self.url, {'assertion': 'good'})
        eq_(res.status_code, 200)
        set_user_mock.assert_called_with(mock.ANY, 'a@a.com')

    @mock.patch('webpay.auth.views.verify_assertion')
    @mock.patch('webpay.auth.views.set_user')
    def test_good_unverified(self, set_user_mock, verify_assertion):
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


@mock.patch.object(auth_views, 'verify_assertion', lambda *a: good_assertion)
class TestBuyerHasPin(SessionTestCase):

    def do_auth(self):
        res = self.client.post(reverse('auth.verify'), {'assertion': 'good'})
        eq_(res.status_code, 200, res)
        return json.loads(res.content)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_no_user(self, slumber):
        slumber.generic.buyer.get.return_value = {
            'meta': {'total_count': 0}
        }
        data = self.do_auth()
        eq_(self.client.session.get('uuid_has_pin'), False)
        eq_(data['has_pin'], False)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_no_pin(self, slumber):
        slumber.generic.buyer.get.return_value = {
            'meta': {'total_count': 1},
            'objects': [{'pin': False,
                         'needs_pin_reset': False}]
        }
        self.do_auth()
        eq_(self.client.session.get('uuid_has_pin'), False)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_with_pin(self, slumber):
        slumber.generic.buyer.get.return_value = {
            'meta': {'total_count': 1},
            'objects': [{'pin': True,
                         'needs_pin_reset': False}]
        }
        data = self.do_auth()
        eq_(self.client.session.get('uuid_has_pin'), True)
        eq_(data['has_pin'], True)
        eq_(data['pin_create'], reverse('pin.create'))


@mock.patch.object(auth_views, 'verify_assertion', lambda *a: good_assertion)
class TestBuyerHasResetFlag(SessionTestCase):

    def do_auth(self):
        res = self.client.post(reverse('auth.verify'), {'assertion': 'good'})
        eq_(res.status_code, 200, res)
        return json.loads(res.content)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_no_user(self, slumber):
        slumber.generic.buyer.get.return_value = {
            'meta': {'total_count': 0}
        }
        self.do_auth()
        eq_(self.client.session.get('uuid_reset_pin'), False)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_no_reset_pin_flag(self, slumber):
        slumber.generic.buyer.get.return_value = {
            'meta': {'total_count': 1},
            'objects': [{'pin': True,
                         'needs_pin_reset': False}]
        }
        self.do_auth()
        eq_(self.client.session.get('uuid_reset_pin'), False)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_with_reset_pin_flag(self, slumber):
        slumber.generic.buyer.get.return_value = {
            'meta': {'total_count': 1},
            'objects': [{'pin': True,
                         'needs_pin_reset': True}]
        }
        self.do_auth()
        eq_(self.client.session.get('uuid_reset_pin'), True)
