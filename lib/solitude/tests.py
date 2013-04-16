import json

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

import mock
from nose.exc import SkipTest
from nose.tools import eq_

from lib.solitude.api import client, SellerNotConfigured
from lib.solitude.errors import ERROR_STRINGS
from webpay.pay.models import Issuer


class SolitudeAPITest(TestCase):

    def setUp(self):
        self.uuid = 'dat:uuid'
        self.pin = '1234'

    @classmethod
    def setUpClass(cls):
        # TODO(Wraithan): Add a mocked backend so we have idempotent tests.
        if (getattr(settings, 'SOLITUDE_URL', None)
            in [None, 'http://example.com']):
            raise SkipTest
        client.create_buyer('dat:uuid', '1234')

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

    def test_confirm_pin_with_good_pin(self):
        uuid = 'confirm_pin_good_pin'
        client.create_buyer(uuid, self.pin)
        assert client.confirm_pin(uuid, self.pin)

    def test_confirm_pin_with_bad_pin(self):
        uuid = 'confirm_pin_bad_pin'
        client.create_buyer(uuid, self.pin)
        assert not client.confirm_pin(uuid, self.pin[::-1])

    def test_verify_with_confirm_and_good_pin(self):
        uuid = 'verify_pin_confirm_pin_good_pin'
        client.create_buyer(uuid, self.pin)
        assert client.confirm_pin(uuid, self.pin)
        assert client.verify_pin(uuid, self.pin)

    def test_verify_without_confirm_and_good_pin(self):
        uuid = 'verify_pin_good_pin'
        client.create_buyer(uuid, self.pin)
        assert not client.verify_pin(uuid, self.pin)

    def test_verify_alpha_pin(self):
        assert not client.verify_pin(self.uuid, 'lame')

    def test_reset_pin_flag_set(self):
        # set
        client.set_new_pin(self.uuid, '1234')
        res = client.set_needs_pin_reset(self.uuid)
        eq_(res, {})
        buyer = client.get_buyer(self.uuid)
        assert buyer['needs_pin_reset']
        assert not buyer['new_pin']

        # unset
        client.set_new_pin(self.uuid, '1234')
        res = client.set_needs_pin_reset(self.uuid, False)
        eq_(res, {})
        buyer = client.get_buyer(self.uuid)
        assert not buyer['needs_pin_reset']
        assert not buyer['new_pin']

    def test_set_new_pin_for_reset(self):
        uuid = 'set_new_pin_for_reset'
        client.create_buyer(uuid, self.pin)
        eq_(client.set_new_pin(uuid, '1122'), {})

    def test_set_new_pin_for_reset_with_alpha_pin(self):
        uuid = 'set_new_pin_for_reset_with_alpha_pin'
        client.create_buyer(uuid, self.pin)
        res = client.set_new_pin(uuid, 'meow')
        assert res.get('errors')
        eq_(res['errors'].get('new_pin'),
            [ERROR_STRINGS['PIN may only consists of numbers']])

    def test_reset_confirm_pin_with_good_pin(self):
        uuid = 'reset_confirm_pin_good_pin'
        new_pin = '1122'
        client.create_buyer(uuid, self.pin)
        client.set_new_pin(uuid, new_pin)
        assert client.reset_confirm_pin(uuid, new_pin)
        assert client.verify_pin(uuid, new_pin)

    def test_reset_confirm_pin_with_bad_pin(self):
        uuid = 'reset_confirm_pin_bad_pin'
        new_pin = '1122'
        client.create_buyer(uuid, self.pin)
        client.set_new_pin(uuid, new_pin)
        assert client.reset_confirm_pin(uuid, new_pin)
        assert client.verify_pin(uuid, new_pin)
        assert not client.reset_confirm_pin(uuid, self.pin)
        assert client.verify_pin(uuid, new_pin)


class CreateBangoTest(TestCase):
    uuid = 'some:pin'
    seller = {'bango': {'seller': 's', 'resource_uri': 'r',
                        'package_id': '1234'},
              'resource_pk': 'foo'}

    def test_create_no_bango(self):
        with self.assertRaises(ValueError):
            client.create_product('ext:id', None,
                                  {'bango': None, 'resource_pk': 'foo'})

    @mock.patch('lib.solitude.api.client.slumber')
    def test_create_bango(self, slumber):
        # Temporary mocking. Remove when this is mocked properly.
        slumber.bango.generic.post.return_value = {'product': 'some:uri'}
        slumber.bango.product.post.return_value = {'resource_uri': 'some:uri',
                                                   'bango_id': '5678'}
        assert client.create_product('ext:id', 'product:name', self.seller)
        assert slumber.generic.product.post.called
        kw = slumber.generic.product.post.call_args[0][0]
        eq_(kw['external_id'], 'ext:id')
        eq_(slumber.bango.rating.post.call_count, 2)
        assert slumber.bango.premium.post.called

    @mock.patch('lib.solitude.api.client.slumber')
    def test_no_seller(self, slumber):
        slumber.generic.seller.get_object.side_effect = ObjectDoesNotExist
        with self.assertRaises(SellerNotConfigured):
            client.configure_product_for_billing(*range(0, 7))

    @mock.patch('lib.solitude.api.client.slumber')
    def test_no_bango(self, slumber):
        slumber.generic.seller.get_object.return_value = self.seller
        slumber.bango.billing.post.return_value = {
            'billingConfigurationId': 'bar'}
        slumber.bango.product.get_object.side_effect = ObjectDoesNotExist
        eq_(client.configure_product_for_billing(*range(0, 7)), ('bar', 'foo'))

    @mock.patch('lib.solitude.api.client.slumber')
    def test_has_bango(self, slumber):
        slumber.generic.seller.get_object.return_value = self.seller
        slumber.bango.billing.post.return_value = {
            'billingConfigurationId': 'bar'}
        slumber.bango.product.get_object.return_value = {'resource_uri': 'foo'}
        eq_(client.configure_product_for_billing(*range(0, 7)), ('bar', 'foo'))


@mock.patch('lib.solitude.api.client.slumber')
class TransactionTest(TestCase):

    def test_no_transaction(self, slumber):
        slumber.generic.transaction.get.return_value = {'objects': []}
        with self.assertRaises(ValueError):
            client.get_transaction('x')

    def test_multiple_transactions(self, slumber):
        slumber.generic.transaction.get.return_value = {'objects': [1, 2]}
        with self.assertRaises(ValueError):
            client.get_transaction('x')

    def test_notes_transactions(self, slumber):
        slumber.generic.transaction.get.return_value = {'objects': [
            {'notes': json.dumps({'foo': 'bar'})}
        ]}
        trans = client.get_transaction('x')
        eq_(trans['notes'], {'foo': 'bar'})

    def test_notes_issuer_transactions(self, slumber):
        iss = Issuer.objects.create()
        slumber.generic.transaction.get.return_value = {'objects': [
            {'notes': json.dumps({'issuer': iss.pk})}
        ]}
        trans = client.get_transaction('x')
        eq_(trans['notes']['issuer'], iss)
