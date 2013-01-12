from datetime import datetime, timedelta
from unittest import TestCase

from django import http
from django.conf import settings

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
        self.request.session['last_pin_success'] = (datetime.now() -
            timedelta(seconds=settings.PIN_UNLOCK_LENGTH + 60))
        assert not utils.pin_recently_entered(self.request)
