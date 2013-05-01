from datetime import datetime, timedelta
from unittest import TestCase

from django import http
from django.conf import settings

import mock

from webpay.pin import utils


class PinRecentlyEnteredTestCase(TestCase):

    def setUp(self):
        self.request = http.HttpRequest()
        self.request.session = {}

    def test_pin_never_entered(self):
        assert not utils.pin_recently_entered(self.request)

    def test_pin_recenlty_entered_successfully(self):
        self.request.session['last_pin_success'] = datetime.now()
        assert utils.pin_recently_entered(self.request)

    def test_pin_entered_after_timeout(self):
        self.request.session['last_pin_success'] = (
            datetime.now() - timedelta(seconds=settings.PIN_UNLOCK_LENGTH + 60)
        )
        assert not utils.pin_recently_entered(self.request)


class HasPinTestCase(TestCase):

    def setUp(self):
        self.request = http.HttpRequest()
        self.request.session = {'uuid': 'some uuid'}

    @mock.patch('lib.solitude.api.client.change_pin')
    def test_no_pin_not_confirmed(self, change_pin):
        self.request.session['uuid_has_pin'] = False
        self.request.session['uuid_has_confirmed_pin'] = False
        assert not utils.has_pin(self.request)
        assert not change_pin.called

    @mock.patch('lib.solitude.api.client.change_pin')
    def test_has_pin_not_confirmed(self, change_pin):
        self.request.session['uuid_has_pin'] = True
        self.request.session['uuid_has_confirmed_pin'] = False
        assert not utils.has_pin(self.request)
        assert change_pin.called
        assert not self.request.session['uuid_has_pin']

    @mock.patch('lib.solitude.api.client.change_pin')
    def test_has_pin_is_confirmed(self, change_pin):
        self.request.session['uuid_has_pin'] = True
        self.request.session['uuid_has_confirmed_pin'] = True
        assert utils.has_pin(self.request)
        assert not change_pin.called
