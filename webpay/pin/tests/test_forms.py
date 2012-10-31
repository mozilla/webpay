from django.test import TestCase
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
        assert 'Buyer already has a PIN' in str(form.errors)

    def test_too_long_pin(self):
        self.data.update({'pin': 'way too long pin'})
        form = forms.CreatePinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert 'has at most 4' in str(form.errors['pin'])


class VerifyPinFormTest(BasePinFormTestCase):

    @patch.object(client, 'verify_pin', lambda x, y: True)
    def test_correct_pin(self):
        form = forms.VerifyPinForm(uuid=self.uuid, data=self.data)
        assert form.is_valid()

    @patch.object(client, 'verify_pin', lambda x, y: False)
    def test_incorrect_pin(self):
        form = forms.VerifyPinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert 'Incorrect PIN' in str(form.errors)

    def test_too_long_pin(self):
        self.data.update({'pin': 'way too long pin'})
        form = forms.VerifyPinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert 'has at most 4' in str(form.errors['pin'])


class ChangePinFormTest(BasePinFormTestCase):

    def setUp(self):
        super(ChangePinFormTest, self).setUp()
        self.data = {'old_pin': 'old', 'pin': 'new'}

    @patch.object(client, 'verify_pin', lambda x, y: True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': x})
    def test_correct_pin(self):
        form = forms.ChangePinForm(uuid=self.uuid, data=self.data)
        assert form.is_valid()
        assert hasattr(form, 'buyer')

    @patch.object(client, 'verify_pin', lambda x, y: False)
    def test_incorrect_pin(self):
        form = forms.ChangePinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert 'Incorrect PIN' in str(form.errors)

    @patch.object(client, 'verify_pin', lambda x, y: False)
    def test_too_long_pin(self):
        self.data.update({'pin': 'way too long pin'})
        form = forms.ChangePinForm(uuid=self.uuid, data=self.data)
        assert not form.is_valid()
        assert 'has at most 4' in str(form.errors['pin'])
