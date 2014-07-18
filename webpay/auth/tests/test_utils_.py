from datetime import datetime

from django import http, test
from django.conf import settings
from django.core.exceptions import PermissionDenied

import mock
from nose.tools import eq_
from webpay.auth.utils import check_whitelist, get_uuid, set_user


@mock.patch.object(settings, 'DOMAIN', 'web.pay')
class TestUUID(test.TestCase):

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


class TestWhitelist(test.TestCase):

    def test_none(self):
        with self.settings(USER_WHITELIST=[]):
            eq_(check_whitelist('whatever'), True)

    def test_wildcard(self):
        emails = [('foo@mozilla.com', True),
                  ('blah@mozilla.not.really', False)]

        with self.settings(USER_WHITELIST=['^.*?@mozilla\.com$']):
            for email, result in emails:
                eq_(check_whitelist(email), result)
