from django.conf import settings
from django.test import TestCase

from nose.exc import SkipTest
from nose.tools import eq_

from lib.solitude.api import client


class SolitudeAPITest(TestCase):

    def setUp(self):
        self.uuid = 'dat:uuid'
        self.pin = '1234'

    @classmethod
    def setUpClass(cls):
        # TODO(Wraithan): Add a mocked backend so we have idempotent tests.
        if getattr(settings, 'SOLITUDE_URL', None) is None:
            raise SkipTest
        client.create_buyer('dat:uuid', '1234')

    def test_change_pin(self):
        buyer_id = client.get_buyer(self.uuid)['id']
        assert client.change_pin(buyer_id, '4321')
        assert client.verify_pin(self.uuid, '4321')
        assert client.change_pin(buyer_id, self.pin)

    def test_get_buyer(self):
        buyer = client.get_buyer(self.uuid)
        eq_(buyer.get('uuid'), self.uuid)
        assert buyer.get('pin')
        assert buyer.get('id')

    def test_non_existent_get_buyer(self):
        buyer = client.get_buyer('something that does not exist')
        assert not buyer

    def test_create_buyer_without_pin(self):
        uuid = 'no_pin:1234'
        buyer = client.create_buyer(uuid)
        eq_(buyer.get('uuid'), uuid)
        assert not buyer.get('pin')
        assert buyer.get('id')

    def test_create_buyer_with_pin(self):
        uuid = 'with_pin:!234'
        buyer = client.create_buyer(uuid, self.pin)
        eq_(buyer.get('uuid'), uuid)
        assert buyer.get('pin')
        assert buyer.get('id')

    def test_verify_pin(self):
        assert client.verify_pin(self.uuid, self.pin)

    def test_verify_pin(self):
        assert not client.verify_pin(self.uuid, 'lame')
