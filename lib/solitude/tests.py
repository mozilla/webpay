import json

from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

import mock
from nose.tools import eq_
from slumber.exceptions import HttpClientError

from lib.solitude.api import client, SellerNotConfigured
from lib.solitude.errors import ERROR_STRINGS
from lib.solitude.exceptions import ResourceNotModified


@mock.patch('lib.solitude.api.client.slumber')
class SolitudeAPITest(TestCase):

    def setUp(self):
        self.uuid = 'dat:uuid'
        self.pin = '1234'
        self.buyer_data = {
            'uuid': self.uuid,
            'pin': self.pin,
            'resource_pk': '5678',
            'etag': 'etag:test'
        }

    def create_error_response(self, status_code=400, content=None):
        if content is None:
            content = {'ERROR': ['This field is required.']}

        class FakeResponse(object):
            pass

        error_response = FakeResponse()
        error_response.status_code = status_code
        error_response.content = content
        return error_response

    def test_get_buyer(self, slumber):
        slumber.generic.buyer.get.return_value = self.buyer_data
        buyer = client.get_buyer(self.uuid)
        eq_(buyer.get('uuid'), self.uuid)
        assert buyer.get('pin')
        assert buyer.get('id')
        assert buyer.get('etag')

    def test_get_buyer_with_etag(self, slumber):
        slumber.generic.buyer.get.return_value = self.buyer_data
        buyer = client.get_buyer(self.uuid)
        eq_(buyer.get('uuid'), self.uuid)
        slumber.generic.buyer.get.side_effect = ResourceNotModified()
        buyer2 = client.get_buyer(self.uuid)
        eq_(buyer.get('etag'), buyer2.get('etag'))

    def test_non_existent_get_buyer(self, slumber):
        slumber.generic.buyer.get.side_effect = HttpClientError(
            response=self.create_error_response())
        buyer = client.get_buyer('something that does not exist')
        assert 'errors' in buyer

    def test_create_buyer_without_pin(self, slumber):
        uuid = 'no_pin:1234'
        self.buyer_data['uuid'] = uuid
        del self.buyer_data['pin']
        slumber.generic.buyer.post.return_value = self.buyer_data
        buyer = client.create_buyer(uuid)
        eq_(buyer.get('uuid'), uuid)
        assert not buyer.get('pin')
        assert buyer.get('id')

    def test_create_buyer_with_pin(self, slumber):
        uuid = 'with_pin'
        self.buyer_data['uuid'] = uuid
        slumber.generic.buyer.post.return_value = self.buyer_data
        buyer = client.create_buyer(uuid, self.pin)
        eq_(buyer.get('uuid'), uuid)
        assert buyer.get('pin')
        assert buyer.get('id')

    def test_create_buyer_with_alpha_pin(self, slumber):
        slumber.generic.buyer.post.side_effect = HttpClientError(
            response=self.create_error_response(content={
                'pin': ['PIN may only consists of numbers']
            }))
        buyer = client.create_buyer('with_alpha_pin', 'lame')
        assert buyer.get('errors')
        eq_(buyer['errors'].get('pin'),
            [ERROR_STRINGS['PIN may only consists of numbers']])

    def test_create_buyer_with_short_pin(self, slumber):
        slumber.generic.buyer.post.side_effect = HttpClientError(
            response=self.create_error_response(content={
                'pin': ['PIN must be exactly 4 numbers long']
            }))
        buyer = client.create_buyer('with_short_pin', '123')
        assert buyer.get('errors')
        eq_(buyer['errors'].get('pin'),
            [ERROR_STRINGS['PIN must be exactly 4 numbers long']])

    def test_create_buyer_with_long_pin(self, slumber):
        slumber.generic.buyer.post.side_effect = HttpClientError(
            response=self.create_error_response(content={
                'pin': ['PIN must be exactly 4 numbers long']
            }))
        buyer = client.create_buyer('with_long_pin', '12345')
        assert buyer.get('errors')
        eq_(buyer['errors'].get('pin'),
            [ERROR_STRINGS['PIN must be exactly 4 numbers long']])

    def test_create_buyer_with_existing_uuid(self, slumber):
        slumber.generic.buyer.post.side_effect = HttpClientError(
            response=self.create_error_response(content={
                'uuid': ['Buyer with this Uuid already exists.']
            }))
        buyer = client.create_buyer(self.uuid, '1234')
        assert buyer.get('errors')
        eq_(buyer['errors'].get('uuid'),
            [ERROR_STRINGS['Buyer with this Uuid already exists.']])

    def test_confirm_pin_with_good_pin(self, slumber):
        slumber.generic.confirm_pin.post.return_value = {'confirmed': True}
        assert client.confirm_pin(self.uuid, self.pin)

    def test_confirm_pin_with_bad_pin(self, slumber):
        slumber.generic.confirm_pin.post.return_value = {'confirmed': False}
        assert not client.confirm_pin(self.uuid, self.pin[::-1])

    def test_verify_pin_with_confirm(self, slumber):
        slumber.generic.verify_pin.post.return_value = {'valid': True}
        assert client.verify_pin(self.uuid, self.pin)['valid']

    def test_verify_pin_without_confirm(self, slumber):
        slumber.generic.verify_pin.post.return_value = {'valid': False}
        assert not client.verify_pin(self.uuid, self.pin)['valid']

    def test_verify_alpha_pin(self, slumber):
        slumber.generic.verify_pin.post.side_effect = HttpClientError(
            response=self.create_error_response(content={
                'pin': ['PIN may only consists of numbers']
            }))
        assert 'pin' in client.verify_pin(self.uuid, 'lame')['errors']

    def test_set_new_pin_for_reset(self, slumber):
        slumber.generic.set_new_pin.patch.return_value = {}
        eq_(client.set_new_pin(self.uuid, '1122'), {})

    def test_set_new_pin_for_reset_with_good_etag(self, slumber):
        etag = 'etag:good'
        slumber.generic.set_new_pin.patch.return_value = {}
        eq_(client.set_new_pin(self.uuid, '1122', etag), {})

    def test_set_new_pin_for_reset_with_alpha_pin(self, slumber):
        buyer = mock.Mock(return_value=self.buyer_data)
        buyer.patch.side_effect = HttpClientError(
            response=self.create_error_response(content={
                'new_pin': ['PIN may only consists of numbers']
            }))
        slumber.generic.buyer.return_value = buyer
        res = client.set_new_pin(self.uuid, 'meow')
        assert res.get('errors')
        eq_(res['errors'].get('new_pin'),
            [ERROR_STRINGS['PIN may only consists of numbers']])

    def test_set_new_pin_for_reset_with_bad_etag(self, slumber):
        wrong_etag = 'etag:wrong'
        buyer = mock.Mock(return_value=self.buyer_data)
        buyer.patch.side_effect = HttpClientError(
            response=self.create_error_response(
                status_code=412,
                content={'ERROR': [('The resource has been modified, '
                                          'please re-fetch it.')]}))
        slumber.generic.buyer.return_value = buyer
        res = client.set_new_pin(self.uuid, self.pin, wrong_etag)
        assert res.get('errors')
        eq_(res['errors'],
        [ERROR_STRINGS['The resource has been modified, please re-fetch it.']])

    def test_reset_confirm_pin_with_good_pin(self, slumber):
        new_pin = '1122'
        buyer = mock.Mock(return_value=self.buyer_data)
        buyer.patch.return_value = {}
        slumber.generic.buyer.return_value = buyer
        client.set_new_pin(self.uuid, new_pin)
        slumber.generic.reset_confirm_pin.post.return_value = {
            'confirmed': True
        }
        assert client.reset_confirm_pin(self.uuid, new_pin)

    def test_reset_confirm_pin_with_bad_pin(self, slumber):
        new_pin = '1122'
        buyer = mock.Mock(return_value=self.buyer_data)
        buyer.patch.return_value = {}
        slumber.generic.buyer.return_value = buyer
        client.set_new_pin(self.uuid, new_pin)
        slumber.generic.reset_confirm_pin.post.return_value = {
            'confirmed': False
        }
        assert not client.reset_confirm_pin(self.uuid, new_pin)

    def test_change_pin_to_remove_existing_pin(self, slumber):
        new_pin = None
        buyer = mock.Mock(return_value=self.buyer_data)
        buyer.patch.return_value = {}
        slumber.generic.buyer.return_value = buyer
        assert 'errors' not in client.change_pin(self.uuid, new_pin)

    def test_change_pin_with_existing_pin(self, slumber):
        buyer = mock.Mock(return_value=self.buyer_data)
        buyer.patch.return_value = {}
        slumber.generic.buyer.return_value = buyer
        assert 'errors' not in client.change_pin(self.uuid, self.pin)

    def test_change_pin_with_etag(self, slumber):
        etag = 'etag:good'
        buyer = mock.Mock(return_value=self.buyer_data)
        buyer.patch.return_value = {}
        slumber.generic.buyer.return_value = buyer
        assert 'errors' not in client.change_pin(self.uuid, self.pin, etag)

    def test_change_pin_with_wrong_etag(self, slumber):
        wrong_etag = 'etag:wrong'
        buyer = mock.Mock(return_value=self.buyer_data)
        buyer.patch.side_effect = HttpClientError(
            response=self.create_error_response(
                status_code=412,
                content={'ERROR': [('The resource has been modified, '
                                          'please re-fetch it.')]}))
        slumber.generic.buyer.return_value = buyer
        res = client.change_pin(self.uuid, self.pin, wrong_etag)
        assert 'errors' in res
        eq_(res['errors'],
        [ERROR_STRINGS['The resource has been modified, please re-fetch it.']])

    def test_set_needs_pin_reset(self, slumber):
        buyer = mock.Mock(return_value=self.buyer_data)
        buyer.patch.return_value = {}
        slumber.generic.buyer.return_value = buyer
        res = client.set_needs_pin_reset(self.uuid)
        eq_(res, {})

    def test_set_needs_pin_reset_with_good_etag(self, slumber):
        etag = 'etag:good'
        buyer = mock.Mock(return_value=self.buyer_data)
        buyer.patch.return_value = {}
        slumber.generic.buyer.return_value = buyer
        res = client.set_needs_pin_reset(self.uuid, etag=etag)
        eq_(res, {})

    def test_set_needs_pin_reset_with_wrong_etag(self, slumber):
        wrong_etag = 'etag:wrong'
        buyer = mock.Mock(return_value=self.buyer_data)
        buyer.patch.side_effect = HttpClientError(
            response=self.create_error_response(
                status_code=412,
                content={'ERROR': [('The resource has been modified, '
                                          'please re-fetch it.')]}))
        slumber.generic.buyer.return_value = buyer
        res = client.set_needs_pin_reset(self.uuid, etag=wrong_etag)
        assert 'errors' in res
        eq_(res['errors'],
        [ERROR_STRINGS['The resource has been modified, please re-fetch it.']])

    def test_unset_needs_pin_reset(self, slumber):
        buyer = mock.Mock(return_value=self.buyer_data)
        buyer.patch.return_value = {}
        slumber.generic.buyer.return_value = buyer
        res = client.set_needs_pin_reset(self.uuid, False)
        eq_(res, {})

    def test_unset_needs_pin_reset_with_good_etag(self, slumber):
        etag = 'etag:good'
        buyer = mock.Mock(return_value=self.buyer_data)
        buyer.patch.return_value = {}
        slumber.generic.buyer.return_value = buyer
        res = client.set_needs_pin_reset(self.uuid, False, etag=etag)
        eq_(res, {})

    def test_unset_needs_pin_reset_with_wrong_etag(self, slumber):
        wrong_etag = 'etag:wrong'
        buyer = mock.Mock(return_value=self.buyer_data)
        buyer.patch.side_effect = HttpClientError(
            response=self.create_error_response(
                status_code=412,
                content={'ERROR': [('The resource has been modified, '
                                          'please re-fetch it.')]}))
        slumber.generic.buyer.return_value = buyer
        res = client.set_needs_pin_reset(self.uuid, False, etag=wrong_etag)
        assert 'errors' in res
        eq_(res['errors'],
        [ERROR_STRINGS['The resource has been modified, please re-fetch it.']])


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
            client.configure_product_for_billing(*range(0, 10))

    @mock.patch('lib.solitude.api.client.slumber')
    def test_no_bango(self, slumber):
        slumber.generic.seller.get_object.return_value = self.seller
        slumber.bango.billing.post.return_value = {
            'billingConfigurationId': 'bar'}
        slumber.bango.product.get_object.side_effect = ObjectDoesNotExist
        eq_(client.configure_product_for_billing(*range(0, 10)), ('bar', 'foo'))

    @mock.patch('lib.solitude.api.client.slumber')
    def test_has_bango(self, slumber):
        slumber.generic.seller.get_object.return_value = self.seller
        slumber.bango.billing.post.return_value = {
            'billingConfigurationId': 'bar'}
        slumber.bango.product.get_object.return_value = {'resource_uri': 'foo'}
        eq_(client.configure_product_for_billing(*range(0, 10)), ('bar', 'foo'))


@mock.patch('lib.solitude.api.client.slumber')
class TransactionTest(TestCase):

    def test_notes_transactions(self, slumber):
        slumber.generic.transaction.get_object.return_value = {
                'notes': json.dumps({'foo': 'bar'})
        }
        trans = client.get_transaction('x')
        eq_(trans['notes'], {'foo': 'bar'})
