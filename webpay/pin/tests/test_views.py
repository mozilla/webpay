from django.core.urlresolvers import reverse
from django.test import TestCase
from mock import patch

from lib.solitude.api import client


class PinViewTestCase(TestCase):
    url_name = ''

    def setUp(self):
        self.url = reverse(self.url_name)


class CreatePinViewTest(PinViewTestCase):
    url_name = 'pin_create'

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


class VerifyPinViewTest(PinViewTestCase):
    url_name = 'pin_verify'

    @patch.object(client, 'verify_pin', lambda x, y: True)
    def test_good_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert 'Success' in res.content

    @patch.object(client, 'verify_pin', lambda x, y: False)
    def test_bad_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert not 'Success' in res.content


class ChangePinViewTest(PinViewTestCase):
    url_name = 'pin_change'

    @patch('lib.solitude.api.client.change_pin', auto_spec=True)
    @patch.object(client, 'verify_pin', lambda x, y: True)
    def test_good_pin(self, change_pin):
        res = self.client.post(self.url, data={'old_pin': '1234',
                                               'new_pin': '4321'})
        assert change_pin.called
        assert 'Success' in res.content

    @patch('lib.solitude.api.client.change_pin', auto_spec=True)
    @patch.object(client, 'verify_pin', lambda x, y: False)
    def test_bad_pin(self, change_pin):
        res = self.client.post(self.url, data={'old_pin': '1234',
                                               'new_pin': '4321'})
        assert not change_pin.called
        assert not 'Success' in res.content
