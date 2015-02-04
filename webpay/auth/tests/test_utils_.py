from datetime import datetime

from django import http
from django.conf import settings
from django.core.exceptions import PermissionDenied

import mock
from nose.tools import eq_
from webpay.auth.utils import check_whitelist, get_uuid, set_user
from webpay.base.tests import TestCase


@mock.patch.object(settings, 'DOMAIN', 'web.pay')
class TestUUID(TestCase):

    def test_good(self):
        res = get_uuid('f@f.com')
        assert res.startswith('web.pay:')

    def test_unicode(self):
        res = get_uuid(u'f@f.com')
        assert res.startswith('web.pay:')

    def test_bad(self):
        with self.assertRaises(ValueError):
            get_uuid(None)

    @mock.patch('webpay.auth.utils.client')
    def test_set_user(self, client):
        email = 'f@f.com'
        req = mock.MagicMock()
        user = get_uuid(email)
        eq_(set_user(req, email), user)
        assert client.get_buyer.called
        assert req.session.__setitem__.called

    @mock.patch('webpay.auth.utils.client')
    def test_set_user_create_buyer(self, client):
        email = 'f@f.com'
        req = mock.MagicMock()
        user = get_uuid(email)
        client.get_buyer.return_value = {}
        eq_(set_user(req, email), user)
        assert client.get_buyer.called
        assert client.create_buyer.called
        assert req.session.__setitem__.called

    @mock.patch('webpay.auth.utils.client')
    def test_update_user_pin_unlock(self, client):
        email = 'f@f.com'
        req = http.HttpRequest()
        req.session = {
            'last_pin_success': datetime.now()
        }
        user = get_uuid(email)
        eq_(set_user(req, email), user)
        assert req.session['last_pin_success'] is None

    def test_set_with_wildcard(self):
        with self.settings(USER_WHITELIST=['.*?@mozilla.com']):
            with self.assertRaises(PermissionDenied):
                set_user(mock.MagicMock(), 'f@f.com')

    @mock.patch.object(settings, 'UUID_HMAC_KEY', '')
    @mock.patch.object(settings, 'DEBUG', False)
    def test_no_settings(self):
        with self.assertRaises(EnvironmentError):
            get_uuid('f@f.com')


class TestWasReverified(TestCase):
    def setUp(self):
        solitude_client_patcher = mock.patch('webpay.auth.utils.client')
        self.solitude_client = solitude_client_patcher.start()
        self.solitude_client.get_buyer.return_value = {'uuid': '10'}
        self.addCleanup(solitude_client_patcher.stop)

    def test_is_unchanged_if_not_specified(self):
        request = mock.MagicMock()
        request.session = {'was_reverified': 'no way'}
        set_user(request, 'foo@bar.com')
        eq_(request.session['was_reverified'], 'no way')

    def test_is_set_to_true_if_verified(self):
        request = mock.MagicMock()
        request.session = {'was_reverified': 'no way'}
        set_user(request, 'foo@bar.com', verified=True)
        eq_(request.session['was_reverified'], True)

    def test_is_set_to_false_if_verified(self):
        request = mock.MagicMock()
        request.session = {'was_reverified': 'no way'}
        set_user(request, 'foo@bar.com', verified=False)
        eq_(request.session['was_reverified'], False)


class TestWhitelist(TestCase):

    def test_none(self):
        with self.settings(USER_WHITELIST=[]):
            eq_(check_whitelist('whatever'), True)

    def test_wildcard(self):
        emails = [('foo@mozilla.com', True),
                  ('blah@mozilla.not.really', False)]

        with self.settings(USER_WHITELIST=['^.*?@mozilla\.com$']):
            for email, result in emails:
                eq_(check_whitelist(email), result)
