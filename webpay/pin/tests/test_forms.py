from django.test import TestCase

from django_paranoia.signals import finished
from mock import patch
from nose.tools import eq_

from lib.solitude.api import client
from webpay.pin import forms


class BasePinFormTestCase(TestCase):

    def setUp(self):
        self.uuid = 'dat:uuid'
        self.data = {'pin': '1234'}


class PinFormOutputTest(BasePinFormTestCase):

    @patch.object(client, 'get_buyer', lambda x: {})
    def test_html_form_attrs(self):
        form = forms.CreatePinForm(uuid=self.uuid, data=self.data)
        form_html = form.as_p()
        assert 'type="number"' in form_html
        assert 'autocomplete="off"' in form_html
        assert 'placeholder="****"' in form_html
        assert 'x-inputmode="digit"' in form_html
        assert 'max="9999"' in form_html


class CreatePinFormTest(BasePinFormTestCase):

    @patch.object(client, 'get_buyer', lambda x: {'uuid': x})
    def test_existing_buyer(self):
        form = forms.CreatePinForm(uuid=self.uuid, data=self.data)
        assert form.is_valid(), form.errors

    @patch.object(client, 'get_buyer', lambda x: {'uuid:': x, 'pin': 'fake'})
    def test_has_pin(self):
        form = forms.CreatePinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert 'You have already created a PIN.' in str(form.errors)
        eq_(len(form.pin_error_codes), 1)
        eq_(form.pin_error_codes, ['PIN_ALREADY_CREATED'])

    def test_too_long_pin(self):
        self.data.update({'pin': 'way too long pin'})
        form = forms.CreatePinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert 'has at most 4' in str(form.errors['pin'])


class ParanoidPinFormTest(BasePinFormTestCase):
    """Just a smoke test that forms are set up to log to CEF"""

    @patch('django_paranoia.reporters.cef_.log_cef')
    def test_dodgy(self, report):
        data = {'pin': chr(1)}
        forms.CreatePinForm(uuid=self.uuid, data=data)
        finished.send(None, request_meta={}, request_path='/')
        assert report.called


class VerifyPinFormTest(BasePinFormTestCase):

    @patch.object(client, 'verify_pin', lambda x, y: {'locked': False,
                                                      'valid': True})
    def test_correct_pin(self):
        form = forms.VerifyPinForm(uuid=self.uuid, data=self.data)
        assert form.is_valid()
        assert not form.pin_is_locked

    @patch.object(client, 'verify_pin', lambda x, y: {'locked': False,
                                                      'valid': False})
    def test_incorrect_pin(self):
        form = forms.VerifyPinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert 'Wrong pin' in str(form.errors['pin'])
        assert not form.pin_is_locked
        eq_(len(form.pin_error_codes), 1)
        eq_(form.pin_error_codes, ['WRONG_PIN'])

    def test_too_long_pin(self):
        self.data.update({'pin': 'way too long pin'})
        form = forms.VerifyPinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert 'has at most 4' in str(form.errors['pin'])

    @patch.object(client, 'verify_pin', lambda x, y: {'locked': True,
                                                      'valid': False})
    def test_locked_pin(self):
        form = forms.VerifyPinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert form.pin_is_locked


class ConfirmPinFormTest(BasePinFormTestCase):

    @patch.object(client, 'confirm_pin', lambda x, y: True)
    def test_correct_pin(self):
        form = forms.ConfirmPinForm(uuid=self.uuid, data=self.data)
        assert form.is_valid()

    @patch.object(client, 'confirm_pin', lambda x, y: False)
    def test_incorrect_pin(self):
        form = forms.ConfirmPinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert "Pins do not match." in form.errors['pin']
        eq_(len(form.pin_error_codes), 1)
        eq_(form.pin_error_codes, ['PINS_DONT_MATCH'])

    def test_too_long_pin(self):
        self.data.update({'pin': 'way too long pin'})
        form = forms.ConfirmPinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert 'has at most 4' in str(form.errors['pin'])


class ResetConfirmPinFormTest(BasePinFormTestCase):

    @patch.object(client, 'reset_confirm_pin', lambda x, y: True)
    def test_correct_pin(self):
        form = forms.ResetConfirmPinForm(uuid=self.uuid, data=self.data)
        assert form.is_valid()

    @patch.object(client, 'reset_confirm_pin', lambda x, y: False)
    def test_incorrect_pin(self):
        form = forms.ResetConfirmPinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert "Pins do not match." in form.errors['pin']
        eq_(len(form.pin_error_codes), 1)
        eq_(form.pin_error_codes, ['PINS_DONT_MATCH'])

    def test_too_long_pin(self):
        self.data.update({'pin': 'way too long pin'})
        form = forms.ResetConfirmPinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert 'has at most 4' in str(form.errors['pin'])
