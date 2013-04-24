from django.test import TestCase
from django.test.client import RequestFactory

from django_paranoia.signals import finished
from mock import patch

from lib.solitude.api import client
from webpay.pin import forms


class BasePinFormTestCase(TestCase):

    def setUp(self):
        self.uuid = 'dat:uuid'
        self.data = {'pin': '1234'}


class CreatePinFormTest(BasePinFormTestCase):

    @patch.object(client, 'get_buyer', lambda x: {})
    def test_new_user(self):
        form = forms.CreatePinForm(uuid=self.uuid, data=self.data)
        assert form.is_valid(), form.errors
        assert not hasattr(form, 'buyer')

    @patch.object(client, 'get_buyer', lambda x: {'uuid': x})
    def test_existing_buyer(self):
        form = forms.CreatePinForm(uuid=self.uuid, data=self.data)
        assert form.is_valid(), form.errors
        assert hasattr(form, 'buyer')

    @patch.object(client, 'get_buyer', lambda x: {'uuid:': x, 'pin': 'fake'})
    def test_has_pin(self):
        form = forms.CreatePinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert hasattr(form, 'buyer')
        assert 'You have already created a PIN.' in str(form.errors)

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
        finished.send(None, request=RequestFactory().get('/'))
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
        assert 'incorrectly too many times' in str(form.errors['pin'])
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

    def test_too_long_pin(self):
        self.data.update({'pin': 'way too long pin'})
        form = forms.ResetConfirmPinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert 'has at most 4' in str(form.errors['pin'])
