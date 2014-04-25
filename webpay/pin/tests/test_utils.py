from datetime import datetime, timedelta
from unittest import TestCase

from django import http
from django.conf import settings
from django.core.urlresolvers import reverse

import mock
from nose.tools import eq_

from webpay.pay import get_wait_url
from webpay.pin import utils


@mock.patch.object(settings, 'PIN_UNLOCK_LENGTH', 300)
class CheckPinStatusTestCase(TestCase):

    def setUp(self):
        self.request = http.HttpRequest()
        self.request.session = {
            'uuid': 'some uuid',
            'uuid_has_pin': True,
            'uuid_has_confirmed_pin': True
        }

    def test_pin_is_locked(self):
        self.request.session['uuid_pin_is_locked'] = True
        eq_(utils.check_pin_status(self.request), reverse('pin.is_locked'))

    def test_pin_was_locked(self):
        self.request.session['uuid_pin_was_locked'] = True
        eq_(utils.check_pin_status(self.request), reverse('pin.was_locked'))

    def test_pin_recently_entered_successfully(self):
        self.request.session['last_pin_success'] = datetime.now()
        eq_(utils.check_pin_status(self.request),
            get_wait_url(mock.Mock(session={})))

    def test_locked_out_but_pin_recently_entered_successfully(self):
        self.request.session['last_pin_success'] = datetime.now()
        self.request.session['uuid_pin_is_locked'] = True
        eq_(utils.check_pin_status(self.request), reverse('pin.is_locked'))

    def test_pin_entered_after_timeout(self):
        self.request.session['last_pin_success'] = (
            datetime.now() - timedelta(seconds=settings.PIN_UNLOCK_LENGTH + 60)
        )
        eq_(utils.check_pin_status(self.request), None)

    @mock.patch('lib.solitude.api.client.change_pin')
    def test_no_pin_not_confirmed(self, change_pin):
        self.request.session['uuid_has_pin'] = False
        self.request.session['uuid_has_confirmed_pin'] = False
        eq_(utils.check_pin_status(self.request), reverse('pin.create'))
        assert not change_pin.called

    @mock.patch('lib.solitude.api.client.change_pin')
    def test_check_pin_status_not_confirmed(self, change_pin):
        self.request.session['uuid_has_pin'] = True
        self.request.session['uuid_has_confirmed_pin'] = False
        eq_(utils.check_pin_status(self.request), reverse('pin.create'))
        assert change_pin.called
        assert not self.request.session['uuid_has_pin']

    @mock.patch('lib.solitude.api.client.change_pin')
    def test_check_pin_status_is_confirmed(self, change_pin):
        self.request.session['uuid_has_pin'] = True
        self.request.session['uuid_has_confirmed_pin'] = True
        eq_(utils.check_pin_status(self.request), None)
        assert not change_pin.called
