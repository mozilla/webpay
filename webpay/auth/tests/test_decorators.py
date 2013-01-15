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
