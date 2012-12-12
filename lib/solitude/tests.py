from django.conf import settings
from django.test import TestCase

import mock
from nose.exc import SkipTest
from nose.tools import eq_

from lib.solitude.api import client
from lib.solitude.errors import ERROR_STRINGS


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
        eq_(client.change_pin(buyer_id, '4321'), {})
        assert client.verify_pin(self.uuid, '4321')
        eq_(client.change_pin(buyer_id, self.pin), {})

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
        uuid = 'with_pin'
        buyer = client.create_buyer(uuid, self.pin)
        eq_(buyer.get('uuid'), uuid)
        assert buyer.get('pin')
        assert buyer.get('id')

    def test_create_buyer_with_alpha_pin(self):
        buyer = client.create_buyer('with_alpha_pin', 'lame')
        assert buyer.get('errors')
        eq_(buyer['errors'].get('pin'),
            [ERROR_STRINGS['PIN may only consists of numbers']])

    def test_create_buyer_with_short_pin(self):
        buyer = client.create_buyer('with_short_pin', '123')
        assert buyer.get('errors')
        eq_(buyer['errors'].get('pin'),
            [ERROR_STRINGS['PIN must be exactly 4 numbers long']])

    def test_create_buyer_with_long_pin(self):
        buyer = client.create_buyer('with_long_pin', '12345')
        assert buyer.get('errors')
        eq_(buyer['errors'].get('pin'),
            [ERROR_STRINGS['PIN must be exactly 4 numbers long']])

    def test_create_buyer_with_existing_uuid(self):
        buyer = client.create_buyer(self.uuid, '1234')
        assert buyer.get('errors')
        eq_(buyer['errors'].get('uuid'),
            [ERROR_STRINGS['Buyer with this Uuid already exists.']])

    def test_verify_good_pin(self):
        assert client.verify_pin(self.uuid, self.pin)

    def test_verify_alpha_pin(self):
        assert not client.verify_pin(self.uuid, 'lame')


class CreateBangoTest(TestCase):
    uuid = 'some:pin'

    def test_create_no_bango(self):
        with self.assertRaises(ValueError):
            client.create_product('ext:id', None, None, None,
                                  {'bango': None, 'resource_pk': 'foo'})

    @mock.patch('lib.solitude.api.client.slumber')
    def test_create_bango(self, slumber):
        # Temporary mocking. Remove when this is mocked properly.
        slumber.bango.generic.post.return_value = {'product': 'some:uri'}
        slumber.bango.product.post.return_value = {'resource_uri': 'some:uri'}
        assert client.create_product('ext:id', 'product:name', 'CAD', 1,
                {'bango': {'seller': 's', 'resource_uri': 'r'},
                'resource_pk': 'foo'})
        assert slumber.generic.product.post.called
        assert slumber.bango.rating.post.called
        assert slumber.bango.premium.post.called
