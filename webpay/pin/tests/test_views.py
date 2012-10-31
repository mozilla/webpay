from django.core.urlresolvers import reverse
from django.test import TestCase

from mock import patch
from nose.tools import eq_

from lib.solitude.api import client
from lib.solitude.errors import ERROR_STRINGS
from webpay.pay import get_payment_url


class PinViewTestCase(TestCase):
    url_name = ''

    def setUp(self):
        self.url = reverse(self.url_name)


class CreatePinViewTest(PinViewTestCase):
    url_name = 'pin.create'

    @patch('lib.solitude.api.client.create_buyer', auto_spec=True)
    @patch('lib.solitude.api.client.change_pin', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {})
    def test_buyer_does_not_exist(self, change_pin, create_buyer):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert create_buyer.called
        assert not change_pin.called
        assert 'Success' in res.content

    @patch('lib.solitude.api.client.create_buyer', auto_spec=True)
    @patch('lib.solitude.api.client.change_pin', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': 'some:uuid'})
    def test_buyer_does_exist_with_no_pin(self, change_pin, create_buyer):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert not create_buyer.called
        assert change_pin.called
        assert 'Success' in res.content

    @patch('lib.solitude.api.client.create_buyer', auto_spec=True)
    @patch('lib.solitude.api.client.change_pin', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': 'some:uuid',
                                                  'pin': 'fake'})
    def test_buyer_does_exist_with_pin(self, change_pin, create_buyer):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert not create_buyer.called
        assert not change_pin.called
        assert not 'Success' in res.content

    @patch('lib.solitude.api.client.create_buyer', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': 'some:uuid'})
    @patch.object(client, 'change_pin',
                  lambda x, y: {'errors':
                                {'pin':
                                 ['PIN must be exactly 4 numbers long']}})
    def test_buyer_does_exist_with_short_pin(self, create_buyer):
        res = self.client.post(self.url, data={'pin': '123'})
        assert not create_buyer.called
        form = res.context.get('form')
        eq_(form.errors.get('pin'),
            [ERROR_STRINGS['PIN must be exactly 4 numbers long']])

    @patch('lib.solitude.api.client.create_buyer', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': 'some:uuid'})
    @patch.object(client, 'change_pin',
                  lambda x, y: {'errors':
                                {'pin': ['PIN may only consists of numbers']}})
    def test_buyer_does_exist_with_alpha_pin(self, create_buyer):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert not create_buyer.called
        form = res.context.get('form')
        eq_(form.errors.get('pin'),
            [ERROR_STRINGS['PIN may only consists of numbers']])


class VerifyPinViewTest(PinViewTestCase):
    url_name = 'pin.verify'

    @patch.object(client, 'verify_pin', lambda x, y: True)
    def test_good_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        self.assertRedirects(res, get_payment_url())

    @patch.object(client, 'verify_pin', lambda x, y: False)
    def test_bad_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert not 'Success' in res.content


class ChangePinViewTest(PinViewTestCase):
    url_name = 'pin.change'

    @patch('lib.solitude.api.client.change_pin', auto_spec=True)
    @patch.object(client, 'verify_pin', lambda x, y: True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': x})
    def test_good_pin(self, change_pin):
        res = self.client.post(self.url, data={'old_pin': '1234',
                                               'pin': '4321'})
        assert change_pin.called
        assert 'Success' in res.content

    @patch.object(client, 'change_pin',
                  lambda x, y: {'errors':
                                {'pin': ['PIN may only consists of numbers']}})
    @patch.object(client, 'verify_pin', lambda x, y: True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': x})
    def test_alpha_pin(self):
        res = self.client.post(self.url, data={'old_pin': '1234',
                                               'pin': '4321'})
        form = res.context.get('form')
        eq_(form.errors.get('pin'),
            [ERROR_STRINGS['PIN may only consists of numbers']])
        assert not 'Success' in res.content

    @patch.object(client, 'change_pin',
                  lambda x, y: {'errors':
                                {'pin':
                                 ['PIN must be exactly 4 numbers long']}})
    @patch.object(client, 'verify_pin', lambda x, y: True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': x})
    def test_short_pin(self):
        res = self.client.post(self.url, data={'old_pin': '1234',
                                               'pin': '432'})
        form = res.context.get('form')
        eq_(form.errors.get('pin'),
            [ERROR_STRINGS['PIN must be exactly 4 numbers long']])
        assert not 'Success' in res.content

    @patch('lib.solitude.api.client.change_pin', auto_spec=True)
    @patch.object(client, 'verify_pin', lambda x, y: False)
    def test_bad_pin(self, change_pin):
        res = self.client.post(self.url, data={'old_pin': '0000',
                                               'pin': '4321'})
        assert not change_pin.called
        assert not 'Success' in res.content
