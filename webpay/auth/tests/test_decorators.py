import json

from django.core.urlresolvers import reverse

import mock
from nose.tools import eq_

from webpay.auth import views as auth_views

from . import good_assertion, SessionTestCase


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
        eq_(data['needs_redirect'], True)
        eq_(data['redirect_url'], reverse('pin.create'))

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_no_pin(self, slumber):
        slumber.generic.buyer.get.return_value = {
            'meta': {'total_count': 1},
            'objects': [{'pin': False,
                         'pin_confirmed': False,
                         'needs_pin_reset': False}]
        }
        data = self.do_auth()
        eq_(self.client.session.get('uuid_has_pin'), False)
        eq_(self.client.session.get('uuid_has_confirmed_pin'), False)
        eq_(data['needs_redirect'], True)
        eq_(data['redirect_url'], reverse('pin.create'))

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_with_unconfirmed_pin(self, slumber):
        slumber.generic.buyer.get.return_value = {
            'meta': {'total_count': 1},
            'objects': [{'pin': True,
                         'pin_confirmed': False,
                         'needs_pin_reset': False}]
        }
        data = self.do_auth()
        eq_(self.client.session.get('uuid_has_pin'), False)
        eq_(self.client.session.get('uuid_has_confirmed_pin'), False)
        eq_(data['needs_redirect'], True)
        eq_(data['redirect_url'], reverse('pin.create'))

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_with_confirmed_pin(self, slumber):
        slumber.generic.buyer.get.return_value = {
            'meta': {'total_count': 1},
            'objects': [{'pin': True,
                         'pin_confirmed': True,
                         'needs_pin_reset': False}]
        }
        data = self.do_auth()
        eq_(self.client.session.get('uuid_has_pin'), True)
        eq_(self.client.session.get('uuid_has_confirmed_pin'), True)
        eq_(data['needs_redirect'], False)
        eq_(data['redirect_url'], None)


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
        eq_(self.client.session.get('uuid_needs_pin_reset'), False)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_no_reset_pin_flag(self, slumber):
        slumber.generic.buyer.get.return_value = {
            'meta': {'total_count': 1},
            'objects': [{'pin': True,
                         'needs_pin_reset': False}]
        }
        self.do_auth()
        eq_(self.client.session.get('uuid_needs_pin_reset'), False)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_with_reset_pin_flag(self, slumber):
        slumber.generic.buyer.get.return_value = {
            'meta': {'total_count': 1},
            'objects': [{'pin': True,
                         'needs_pin_reset': True}]
        }
        self.do_auth()
        eq_(self.client.session.get('uuid_needs_pin_reset'), True)


@mock.patch.object(auth_views, 'verify_assertion', lambda *a: good_assertion)
class TestBuyerLockedPinFlags(SessionTestCase):

    def do_auth(self):
        res = self.client.post(reverse('auth.verify'), {'assertion': 'good'})
        eq_(res.status_code, 200, res)
        return json.loads(res.content)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_is_locked_out(self, slumber):
        slumber.generic.buyer.get.return_value = {
            'meta': {'total_count': 1},
            'objects': [{'pin': True,
                         'pin_is_locked_out': True}]
        }
        self.do_auth()
        eq_(self.client.session.get('uuid_pin_is_locked'), True)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_was_locked_out(self, slumber):
        slumber.generic.buyer.get.return_value = {
            'meta': {'total_count': 1},
            'objects': [{'pin': True,
                         'pin_was_locked_out': True}]
        }
        self.do_auth()
        eq_(self.client.session.get('uuid_pin_was_locked'), True)
