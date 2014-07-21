import json

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpRequest

import mock
from nose.tools import eq_

from webpay.auth import views as auth_views
from webpay.auth.decorators import user_can_simulate

from . import good_assertion, SessionTestCase, set_up_no_mkt_account


class Base(SessionTestCase):

    def setUp(self):
        super(Base, self).setUp()
        patch = mock.patch('webpay.auth.views.pay_tasks')
        patch.start()
        self.patches = [patch]

    def tearDown(self):
        super(Base, self).tearDown()
        for p in self.patches:
            p.stop()


@mock.patch.object(auth_views, 'verify_assertion', lambda *a: good_assertion)
class TestBuyerHasPin(Base):

    def setUp(self):
        super(TestBuyerHasPin, self).setUp()
        set_up_no_mkt_account(self)

    def do_auth(self):
        res = self.client.post(reverse('auth.verify'), {'assertion': 'good'})
        eq_(res.status_code, 200, res)
        return json.loads(res.content)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_no_user(self, slumber):
        slumber.generic.buyer.get_object_or_404.side_effect = (
            ObjectDoesNotExist)
        slumber.generic.buyer.post.return_value = {
            'uuid': 'new-user',
        }
        data = self.do_auth()
        eq_(self.client.session.get('uuid_has_pin'), False)
        eq_(data['needs_redirect'], True)
        eq_(data['redirect_url'], reverse('pin.create'))

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_no_pin(self, slumber):
        slumber.generic.buyer.get_object_or_404.return_value = {
            'pin': False, 'pin_confirmed': False, 'needs_pin_reset': False}
        data = self.do_auth()
        eq_(self.client.session.get('uuid_has_pin'), False)
        eq_(self.client.session.get('uuid_has_confirmed_pin'), False)
        eq_(data['needs_redirect'], True)
        eq_(data['redirect_url'], reverse('pin.create'))

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_with_unconfirmed_pin(self, slumber):
        slumber.generic.buyer.get_object_or_404.return_value = {
            'pin': True, 'pin_confirmed': False, 'needs_pin_reset': False}
        data = self.do_auth()
        eq_(self.client.session.get('uuid_has_pin'), False)
        eq_(self.client.session.get('uuid_has_confirmed_pin'), False)
        eq_(data['needs_redirect'], True)
        eq_(data['redirect_url'], reverse('pin.create'))

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_with_confirmed_pin(self, slumber):
        slumber.generic.buyer.get_object_or_404.return_value = {
            'pin': True, 'pin_confirmed': True, 'needs_pin_reset': False}
        data = self.do_auth()
        eq_(self.client.session.get('uuid_has_pin'), True)
        eq_(self.client.session.get('uuid_has_confirmed_pin'), True)
        eq_(data['needs_redirect'], False)
        eq_(data['redirect_url'], None)


@mock.patch.object(auth_views, 'verify_assertion', lambda *a: good_assertion)
class TestBuyerHasResetFlag(Base):

    def setUp(self):
        super(TestBuyerHasResetFlag, self).setUp()
        set_up_no_mkt_account(self)

    def do_auth(self):
        res = self.client.post(reverse('auth.verify'), {'assertion': 'good'})
        eq_(res.status_code, 200, res)
        return json.loads(res.content)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_no_user(self, slumber):
        slumber.generic.buyer.get_object_or_404.side_effect = (
            ObjectDoesNotExist)
        slumber.generic.buyer.post.return_value = {
            'uuid': 'new-user',
        }
        self.do_auth()
        eq_(self.client.session.get('uuid_needs_pin_reset'), False)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_no_reset_pin_flag(self, slumber):
        slumber.generic.buyer.get_object_or_404.return_value = {
            'pin': True, 'needs_pin_reset': False}
        self.do_auth()
        eq_(self.client.session.get('uuid_needs_pin_reset'), False)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_with_reset_pin_flag(self, slumber):
        slumber.generic.buyer.get_object_or_404.return_value = {
            'pin': True, 'needs_pin_reset': True}
        self.do_auth()
        eq_(self.client.session.get('uuid_needs_pin_reset'), True)


@mock.patch.object(auth_views, 'verify_assertion', lambda *a: good_assertion)
class TestBuyerLockedPinFlags(Base):

    def setUp(self):
        super(TestBuyerLockedPinFlags, self).setUp()
        set_up_no_mkt_account(self)

    def do_auth(self):
        res = self.client.post(reverse('auth.verify'), {'assertion': 'good'})
        eq_(res.status_code, 200, res)
        return json.loads(res.content)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_is_locked_out(self, slumber):
        slumber.generic.buyer.get_object_or_404.return_value = {
            'pin': True, 'pin_is_locked_out': True}

        self.do_auth()
        eq_(self.client.session.get('uuid_pin_is_locked'), True)

    @mock.patch('lib.solitude.api.client.slumber')
    def test_user_was_locked_out(self, slumber):
        slumber.generic.buyer.get_object_or_404.return_value = {
            'pin': True, 'pin_was_locked_out': True}
        self.do_auth()
        eq_(self.client.session.get('uuid_pin_was_locked'), True)


class TestUserCanSimulate(Base):

    def setUp(self):
        super(TestUserCanSimulate, self).setUp()
        self.session = {}

    def execute_view(self):
        request = HttpRequest()
        request.session = self.session
        # Wrap a fake view in the decorator then execute it.
        user_can_simulate(lambda r: None)(request)

    def perms(self, p):
        self.session['mkt_permissions'] = p

    def test_admin(self):
        self.perms({'admin': True, 'reviewer': False})
        self.execute_view()

    def test_reviewer(self):
        self.perms({'admin': False, 'reviewer': True})
        self.execute_view()

    def test_both(self):
        self.perms({'admin': True, 'reviewer': True})
        self.execute_view()

    def test_neither(self):
        self.perms({'admin': False, 'reviewer': False})
        with self.assertRaises(PermissionDenied):
            self.execute_view()

    def test_no_data(self):
        # No permissions saved to session.
        with self.assertRaises(PermissionDenied):
            self.execute_view()
