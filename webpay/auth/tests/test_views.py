from django.conf import settings
from django.core.urlresolvers import reverse

import mock
from nose.tools import eq_

from webpay.auth.utils import client

from . import good_assertion, SessionTestCase


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
