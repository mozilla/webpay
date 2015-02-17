from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

import mock

from webpay.auth.decorators import user_can_simulate

from . import good_assertion, SessionTestCase

m = mock.Mock()
m().get_verifier().verify()._response = good_assertion


class TestUserCanSimulate(SessionTestCase):

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
