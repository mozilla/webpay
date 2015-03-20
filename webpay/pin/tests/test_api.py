import json

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse

import mock
from nose import SkipTest
from nose.tools import eq_, ok_

from webpay.api.tests.base import BaseAPICase
from webpay.base import dev_messages as msg
from webpay.base.utils import gmtime


class PIN(BaseAPICase):

    def setUp(self, *args, **kw):
        super(PIN, self).setUp(*args, **kw)
        self.url = reverse('api:pin')


class TestError(PIN):

    def test_error(self):
        # A test that the API returns JSON.
        res = self.client.post(self.url, {}, HTTP_ACCEPT='application/json')
        eq_(res.status_code, 400)
        ok_('error_code', json.loads(res.content))


class TestGet(PIN):

    def test_anon(self):
        self.set_session(uuid=None)
        eq_(self.client.get(self.url).status_code, 403)

    def test_no_pin(self):
        self.solitude.generic.buyer.get_object_or_404.side_effect = (
            ObjectDoesNotExist)
        res = self.client.get(self.url)
        eq_(res.status_code, 200)
        eq_(json.loads(res.content)['pin'], False)

    def test_some_pin(self):
        self.solitude.generic.buyer.get_object_or_404.return_value = {
            'pin': True}
        res = self.client.get(self.url)
        self.solitude.generic.buyer.get_object_or_404.assert_called_with(
            headers={}, uuid=self.uuid)
        eq_(json.loads(res.content)['pin'], True)


class TestPost(PIN):

    def setUp(self):
        super(TestPost, self).setUp()
        p = mock.patch('webpay.pin.api.client')
        self.solitude_client = p.start()
        self.addCleanup(p.stop)

    def post(self, *args, **kw):
        kw.setdefault('HTTP_ACCEPT', 'application/json')
        return self.client.post(self.url, *args, **kw)

    def test_anon(self):
        self.set_session(uuid=None)
        eq_(self.post({}).status_code, 403)

    def test_no_data(self):
        res = self.post({})
        eq_(res.status_code, 400)

    def test_user(self):
        self.solitude.generic.buyer.get_object_or_404.return_value = {
            'pin': False, 'resource_pk': 'abc'}
        res = self.post({'pin': '1234'})
        eq_(res.status_code, 204)
        self.solitude_client.change_pin.assert_called_with(
            self.uuid, '1234', etag='', pin_confirmed=True,
            clear_was_locked=True)

    def test_cant_post_when_user_has_pin(self):
        self.solitude.generic.buyer.get_object_or_404.return_value = {
            'pin': True, 'resource_pk': 'abc'}
        res = self.post({'pin': '1234'})
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data['error_code'], msg.PIN_ALREADY_CREATED)

    def test_pin_must_be_long_enough(self):
        self.solitude.generic.buyer.get_object_or_404.return_value = {
            'pin': False, 'resource_pk': 'abc'}
        self.solitude_client.change_pin.return_value = {
            'errors': {'pin': [msg.PIN_4_NUMBERS_LONG]}
        }
        res = self.post({'pin': '123'})
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data['error_code'], msg.PIN_4_NUMBERS_LONG)

    def test_pin_must_be_numeric(self):
        self.solitude.generic.buyer.get_object_or_404.return_value = {
            'pin': False, 'resource_pk': 'abc'}
        self.solitude_client.change_pin.return_value = {
            'errors': {'pin': [msg.PIN_ONLY_NUMBERS]}
        }
        res = self.post({'pin': 'zzzz'})
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data['error_code'], msg.PIN_ONLY_NUMBERS)


@mock.patch.object(settings, 'REQUIRE_REAUTH_TS_FOR_PIN_RESET', True)
class TestPatch(PIN):

    def setUp(self):
        super(TestPatch, self).setUp()
        self.uuid = '1120933'
        self.start_ts = gmtime() - (60 * 15)  # 15 min ago
        self.auth_at = self.start_ts + (60 * 10)  # 5 min ago
        self.set_session(
            user_reset={'start_ts': self.start_ts,
                        'fxa_auth_ts': self.auth_at},
            uuid=self.uuid)
        solitude_client_patcher = mock.patch('webpay.pin.api.client')
        self.solitude_client = solitude_client_patcher.start()
        self.addCleanup(solitude_client_patcher.stop)

    def patch(self, url, data=None):
        """
        A wrapper around self.client.generic until we upgrade Django
        and get the patch method in the test client.
        """
        if data is None:
            data = {'pin': '1234'}
        return self.client.generic('PATCH', url, data=json.dumps(data),
                                   content_type='application/json',
                                   HTTP_ACCEPT='application/json')

    def test_anon(self):
        self.set_session(uuid=None)
        eq_(self.patch(self.url, data={}).status_code, 403)

    def test_no_data(self):
        res = self.patch(self.url, data={})
        eq_(res.status_code, 400)

    def test_no_user(self):
        # TODO: it looks like the PIN flows doesn't take this into account.
        raise SkipTest

    def test_no_fxa_auth(self):
        self.solitude_client.change_pin.return_value = {}
        self.set_session(user_reset={'start_ts': self.start_ts})
        res = self.patch(self.url)
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data['error_code'], msg.INVALID_PIN_REAUTH)

    def test_no_start_ts(self):
        self.solitude_client.change_pin.return_value = {}
        self.set_session(user_reset={'fxa_auth_ts': self.auth_at})
        res = self.patch(self.url)
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data['error_code'], msg.INVALID_PIN_REAUTH)

    def test_fxa_auth_too_old(self):
        self.solitude_client.change_pin.return_value = {}
        # Make the FxA auth occur before the start of the reset.
        # In other words, the user did not re-enter their password; they
        # re-authed from a cookie or something.
        auth_at = self.start_ts - (60 * 1)
        self.set_session(user_reset={'start_ts': self.start_ts,
                                     'fxa_auth_ts': auth_at})
        res = self.patch(self.url)
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data['error_code'], msg.INVALID_PIN_REAUTH)

    def test_expired_fxa_auth(self):
        self.solitude_client.change_pin.return_value = {}
        # Make an FxA reauth that is technically after the reset start time
        # but make it happen too far after the reset.
        expiry = 60 * 60 * 2
        auth_at = self.start_ts + expiry + 1
        self.set_session(user_reset={'start_ts': self.start_ts,
                                     'fxa_auth_ts': auth_at})
        with self.settings(FXA_PIN_REAUTH_EXPIRY=expiry):
            res = self.patch(self.url)
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data['error_code'], msg.INVALID_PIN_REAUTH)

    def test_bypass_reauth_check_from_settings(self):
        self.solitude_client.change_pin.return_value = {}
        # Simulate a native (B2G >= 2.1) device where fxa_auth_ts isn't set.
        self.set_session(user_reset={'start_ts': self.start_ts})
        with self.settings(REQUIRE_REAUTH_TS_FOR_PIN_RESET=False):
            res = self.patch(self.url)
        eq_(res.status_code, 204)

    def test_bypassed_reauth_doesnt_apply_to_oauth(self):
        self.solitude_client.change_pin.return_value = {}
        # Make an invalid auth time.
        auth_at = self.start_ts - 60
        self.set_session(user_reset={'start_ts': self.start_ts,
                                     'fxa_auth_ts': auth_at})
        # Even though we bypass the reauth check here, it should still fail
        # since a reauth timestamp exists.
        with self.settings(REQUIRE_REAUTH_TS_FOR_PIN_RESET=False):
            res = self.patch(self.url)
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data['error_code'], msg.INVALID_PIN_REAUTH)

    def test_change_successfully(self):
        self.solitude_client.change_pin.return_value = {}
        res = self.patch(self.url, data={'pin': '1234'})
        eq_(res.status_code, 204)
        self.solitude_client.change_pin.assert_called_with(
            self.uuid, '1234', pin_confirmed=True, clear_was_locked=True)
        ok_('user_reset' not in self.client.session,
            'Expected user_reset to be removed: {s}'
            .format(s=self.client.session.items()))


class TestCheck(PIN):

    def setUp(self):
        super(TestCheck, self).setUp()
        self.url = reverse('api:pin.check')

    def test_anon(self):
        self.set_session(uuid=None)
        eq_(self.client.post(self.url).status_code, 403)

    def test_no_data(self):
        res = self.client.post(self.url, data={})
        eq_(res.status_code, 400)

    def test_good(self):
        self.solitude.generic.verify_pin.post.return_value = {'valid': True}
        res = self.client.post(self.url, data={'pin': 1234})
        eq_(res.status_code, 200)

    def test_locked(self):
        self.solitude.generic.verify_pin.post.return_value = {'locked': True}
        res = self.client.post(self.url, data={'pin': 1234})
        eq_(res.status_code, 400)

    def test_wrong(self):
        self.solitude.generic.verify_pin.post.return_value = {'valid': False}
        self.solitude.generic.buyer.get_object_or_404.return_value = {
            'pin': True, 'resource_pk': 'abc'}
        res = self.client.post(self.url, data={'pin': 1234})
        eq_(res.status_code, 400)

    def test_404(self):
        self.solitude.generic.verify_pin.post.side_effect = (
            ObjectDoesNotExist)
        res = self.client.post(self.url, data={'pin': 1234})
        eq_(res.status_code, 404)

    def test_output(self):
        self.solitude.generic.verify_pin.post.return_value = {'valid': False}
        self.solitude.generic.buyer.get_object_or_404.return_value = {
            'pin': True, 'resource_pk': 'abc'}
        res = self.client.post(self.url, data={'pin': 1234})
        eq_(res.status_code, 400)
        data = json.loads(res.content)
        eq_(data, {'pin': True,
                   'pin_locked_out': None,
                   'pin_is_locked_out': None,
                   'pin_was_locked_out': None})
