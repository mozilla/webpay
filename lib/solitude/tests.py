import json

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

import mobile_codes
import mock
from nose.tools import eq_, raises
from slumber.exceptions import HttpClientError

from lib.solitude.api import (BangoProvider, BokuProvider, client,
                              ProviderHelper, SellerNotConfigured)
from lib.solitude.errors import ERROR_STRINGS
from lib.solitude.exceptions import ResourceModified, ResourceNotModified


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
            content = {'ERROR': [ERROR_STRINGS['FIELD_REQUIRED']]}

        class FakeResponse(object):
            pass

        error_response = FakeResponse()
        error_response.status_code = status_code
        error_response.content = content
        return error_response

    def test_get_buyer(self, slumber):
        slumber.generic.buyer.get_object_or_404.return_value = self.buyer_data
        buyer = client.get_buyer(self.uuid)
        eq_(buyer.get('uuid'), self.uuid)
        assert buyer.get('pin')
        assert buyer.get('resource_pk')
        assert buyer.get('etag')

    def test_get_buyer_with_etag(self, slumber):
        slumber.generic.buyer.get_object_or_404.return_value = self.buyer_data
        buyer = client.get_buyer(self.uuid)
        eq_(buyer.get('uuid'), self.uuid)
        slumber.generic.buyer.get_object_or_404.side_effect = (
            ResourceNotModified())
        buyer2 = client.get_buyer(self.uuid)
        eq_(buyer.get('etag'), buyer2.get('etag'))

    def test_non_existent_get_buyer(self, slumber):
        slumber.generic.buyer.get_object_or_404.side_effect = HttpClientError(
            response=self.create_error_response())
        buyer = client.get_buyer('something-that-does-not-exist')
        assert 'errors' in buyer

    def test_create_buyer_without_pin(self, slumber):
        uuid = 'no_pin:1234'
        self.buyer_data['uuid'] = uuid
        del self.buyer_data['pin']
        slumber.generic.buyer.post.return_value = self.buyer_data
        buyer = client.create_buyer(uuid)
        eq_(buyer.get('uuid'), uuid)
        assert not buyer.get('pin')
        assert buyer.get('resource_pk')

    def test_create_buyer_with_pin(self, slumber):
        uuid = 'with_pin'
        self.buyer_data['uuid'] = uuid
        slumber.generic.buyer.post.return_value = self.buyer_data
        buyer = client.create_buyer(uuid, self.pin)
        eq_(buyer.get('uuid'), uuid)
        assert buyer.get('pin')
        assert buyer.get('resource_pk')

    def test_create_buyer_with_alpha_pin(self, slumber):
        slumber.generic.buyer.post.side_effect = HttpClientError(
            response=self.create_error_response(content={
                'pin': ['PIN_ONLY_NUMBERS']
            }))
        buyer = client.create_buyer('with_alpha_pin', 'lame')
        assert buyer.get('errors')
        eq_(buyer['errors'].get('pin'), [ERROR_STRINGS['PIN_ONLY_NUMBERS']])

    def test_create_buyer_with_short_pin(self, slumber):
        slumber.generic.buyer.post.side_effect = HttpClientError(
            response=self.create_error_response(content={
                'pin': ['PIN_4_NUMBERS_LONG']
            }))
        buyer = client.create_buyer('with_short_pin', '123')
        assert buyer.get('errors')
        eq_(buyer['errors'].get('pin'),
            [ERROR_STRINGS['PIN_4_NUMBERS_LONG']])

    def test_create_buyer_with_long_pin(self, slumber):
        slumber.generic.buyer.post.side_effect = HttpClientError(
            response=self.create_error_response(content={
                'pin': ['PIN_4_NUMBERS_LONG']
            }))
        buyer = client.create_buyer('with_long_pin', '12345')
        assert buyer.get('errors')
        eq_(buyer['errors'].get('pin'),
            [ERROR_STRINGS['PIN_4_NUMBERS_LONG']])

    def test_create_buyer_with_existing_uuid(self, slumber):
        slumber.generic.buyer.post.side_effect = HttpClientError(
            response=self.create_error_response(content={
                'uuid': ['BUYER_UUID_ALREADY_EXISTS']
            }))
        buyer = client.create_buyer(self.uuid, '1234')
        assert buyer.get('errors')
        eq_(buyer['errors'].get('uuid'),
            [ERROR_STRINGS['BUYER_UUID_ALREADY_EXISTS']])

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
                'pin': ['PIN_ONLY_NUMBERS']
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
                'new_pin': ['PIN_ONLY_NUMBERS']
            }))
        slumber.generic.buyer.return_value = buyer
        res = client.set_new_pin(self.uuid, 'meow')
        assert res.get('errors')
        eq_(res['errors'].get('new_pin'),
            [ERROR_STRINGS['PIN_ONLY_NUMBERS']])

    def test_set_new_pin_for_reset_with_wrong_etag(self, slumber):
        wrong_etag = 'etag:wrong'
        buyer = mock.Mock(return_value=self.buyer_data)
        buyer.patch.side_effect = HttpClientError(
            response=self.create_error_response(
                status_code=412,
                content={'ERROR': ['RESOURCE_MODIFIED']}))
        slumber.generic.buyer.return_value = buyer
        with self.assertRaises(ResourceModified):
            client.set_new_pin(self.uuid, self.pin, wrong_etag)

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
                content={'ERROR': ['RESOURCE_MODIFIED']}))
        slumber.generic.buyer.return_value = buyer
        with self.assertRaises(ResourceModified):
            client.change_pin(self.uuid, self.pin, wrong_etag)

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
                content={'ERROR': ['RESOURCE_MODIFIED']}))
        slumber.generic.buyer.return_value = buyer
        with self.assertRaises(ResourceModified):
            client.set_needs_pin_reset(self.uuid, etag=wrong_etag)

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
                content={'ERROR': ['RESOURCE_MODIFIED']}))
        slumber.generic.buyer.return_value = buyer
        with self.assertRaises(ResourceModified):
            client.set_needs_pin_reset(self.uuid, False, etag=wrong_etag)


class CreateBangoTest(TestCase):
    uuid = 'some:pin'
    seller = {'bango': {'seller': 's', 'resource_uri': 'r',
                        'package_id': '1234'},
              'resource_uri': '/seller/1',
              'resource_pk': 'seller_pk'}

    def setUp(self):
        super(CreateBangoTest, self).setUp()
        self.slumber = mock.MagicMock()
        self.provider = ProviderHelper('bango', slumber=self.slumber)

    def test_create_without_bango_seller(self):
        with self.assertRaises(ValueError):
            self.provider.create_product(
                'ext:id', 'product name',
                {'bango': None, 'resource_pk': '1',
                 'resource_uri': '/seller/1'},
                generic_product={'resource_pk': '2'})

    def test_create_bango_product(self):
        slumber = self.slumber
        slumber.bango.generic.post.return_value = {'product': 'some:uri'}
        slumber.bango.product.post.return_value = {'resource_uri': 'some:uri',
                                                   'bango_id': '5678'}
        assert self.provider.create_product('ext:id', 'product:name',
                                            self.seller)
        assert slumber.generic.product.post.called
        kw = slumber.generic.product.post.call_args[0][0]
        eq_(kw['external_id'], 'ext:id')
        eq_(slumber.bango.rating.post.call_count, 2)
        assert slumber.bango.premium.post.called

    def test_no_seller(self):
        slumber = self.slumber
        slumber.generic.seller.get_object_or_404.side_effect = (
            ObjectDoesNotExist)
        with self.assertRaises(SellerNotConfigured):
            self.provider.start_transaction(*range(0, 8))

    def test_no_bango_product(self):
        slumber = self.slumber
        slumber.generic.seller.get_object_or_404.return_value = self.seller
        slumber.bango.billing.post.return_value = {
            'billingConfigurationId': 'bill_id'}
        slumber.bango.product.get_object_or_404.side_effect = (
            ObjectDoesNotExist)
        eq_(self.provider.start_transaction(*range(0, 8)),
            ('bill_id', 'seller_pk'))

    def test_with_bango_product(self):
        slumber = self.slumber
        slumber.generic.seller.get_object_or_404.return_value = self.seller
        slumber.bango.billing.post.return_value = {
            'billingConfigurationId': 'bill_id'}
        slumber.bango.product.get_object.return_value = {
            'resource_uri': 'foo'}
        eq_(self.provider.start_transaction(*range(0, 8)),
            ('bill_id', 'seller_pk'))


class ProviderTestCase(TestCase):

    def configure(self, trans_uuid='trans-xyz', seller_uuid='seller-xyz',
                  product_uuid='product-xyz', product_name='Shiny App',
                  success_redirect='/todo/postback',
                  error_redirect='/todo/chargeback',
                  prices=[{'price': '0.89', 'currency': 'EUR'},
                          {'price': '55.00', 'currency': 'MXN'}],
                  icon_url='/todo/icons', user_uuid='user-xyz',
                  app_size=1024 * 5, mcc=None, mnc=None):
        return self.provider.start_transaction(
            trans_uuid,
            seller_uuid,
            product_uuid,
            product_name,
            prices,
            icon_url,
            user_uuid,
            app_size,
            mcc=mcc,
            mnc=mnc
        )

    def set_mocks(self, returns={}, keys=('generic.seller',
                                          'generic.product',
                                          'generic.buyer'),
                  seller_uuid=None, product_uuid=None):
        """
        Set mock object returns, for example:

            self.set_mocks({
                'provider.reference.transactions': {
                    'method': 'post',
                    'return': {
                        'token': 'the-token',
                    }
                }
            })

        That will do the same thing as:

           self.slumber.provider.reference.transactions.post.return_value = {
               'token': 'the-token',
           }

        By default, get_object_or_404 will be mocked with a resource_pk and
        resource_uri
        """
        if seller_uuid and 'generic.seller' not in returns:
            returns['generic.seller'] = {
                'return': {
                    'uuid': seller_uuid,
                    'resource_pk': seller_uuid,
                    'resource_uri': '/seller/' + seller_uuid,
                }
            }
        if product_uuid and 'generic.product' not in returns:
            returns['generic.product'] = {
                'return': {
                    'resource_uri': '/product/' + product_uuid,
                    'uuid': product_uuid,
                    'external_id': product_uuid,
                }
            }

        keys = set(list(keys) + returns.keys())
        for k in keys:
            attr_path = k.split('.')
            api = self.slumber
            while True:
                try:
                    api = getattr(api, attr_path.pop(0))
                except IndexError:
                    break

            conf = returns.get(k, {})
            method = conf.get('method', 'get_object_or_404')
            api = getattr(api, method)
            if conf.get('side_effect'):
                api.side_effect = conf['side_effect']
            else:
                api.return_value = conf.get('return', {
                    'uuid': 1,
                    'resource_pk': 1,
                    'resource_uri': '/something/1',
                })


class TestConfigureRefTrans(ProviderTestCase):

    def setUp(self):
        self.slumber = mock.MagicMock()
        self.provider = ProviderHelper('reference', slumber=self.slumber)

    def set_mocks(self, returns={}, keys=None, **kw):
        if not keys:
            keys = ('generic.seller',
                    'generic.product',
                    'generic.buyer',
                    'provider.reference.products',
                    'provider.reference.transactions',)
        return super(TestConfigureRefTrans, self).set_mocks(
            returns=returns, keys=keys, **kw)

    def test_with_existing_prod(self):
        seller_uuid = 'seller-xyz'
        product_uuid = 'app-xyz'

        self.set_mocks({
            'provider.reference.transactions': {
                'method': 'post',
                'return': {
                    'token': 'zippy-trans-token',
                }
            }},
            seller_uuid=seller_uuid,
            product_uuid=product_uuid
        )

        result = self.configure(seller_uuid=seller_uuid,
                                product_uuid=product_uuid)

        eq_(result[0], 'zippy-trans-token')
        eq_(result[1], seller_uuid)

        kw = self.slumber.provider.reference.products\
                                            .get_object_or_404.call_args[1]
        eq_(kw['external_id'], product_uuid)
        eq_(kw['seller_id'], seller_uuid)

    def test_with_new_prod(self):
        new_product_id = 66
        product_uuid = 'app-xyz'
        seller_uuid = 'seller-xyz'

        self.set_mocks({
            'generic.product': {
                'side_effect': ObjectDoesNotExist,
            },
            'provider.reference.transactions': {
                'method': 'post',
                'return': {
                    'token': 'zippy-trans-token',
                }
            },
            'provider.reference.products': {
                'side_effect': ObjectDoesNotExist,
            },
            'provider.reference.sellers': {
                'return': {
                    'resource_pk': seller_uuid,
                }
            }},
            seller_uuid=seller_uuid
        )

        self.slumber.provider.reference.products.post.return_value = {
            'resource_pk': new_product_id,
        }

        result = self.configure(seller_uuid=seller_uuid,
                                product_uuid=product_uuid)

        eq_(result[0], 'zippy-trans-token')

        kw = self.slumber.provider.reference.products.post.call_args[0][0]
        eq_(kw['external_id'], product_uuid)
        eq_(kw['seller_id'], seller_uuid)

        kw = self.slumber.provider.reference.transactions.post.call_args[0][0]
        eq_(kw['product_id'], new_product_id)
        eq_(kw['product_image_url'], '/todo/icons')
        assert kw['success_url'].endswith('/provider/reference/success'), (
            'Unexpected: {0}'.format(kw['success_url']))
        assert kw['error_url'].endswith('/provider/reference/error'), (
            'Unexpected: {0}'.format(kw['error_url']))

    def test_callback_validation_success(self):
        self.set_mocks({
            'provider.reference.notices': {
                'method': 'post',
                'return': {
                    'result': 'OK',
                }
            },
            'provider.reference.transactions': {
                'method': 'post',
                'return': {
                    'token': 'zippy-trans-token',
                }
            }},
            product_uuid='XYZ'
        )

        self.configure(seller_uuid='seller-xyz', product_uuid='app-xyz')
        is_valid = self.provider.is_callback_token_valid({'foo': 'bar'})
        eq_(is_valid, True)
        eq_(self.slumber.provider.reference.notices.post.call_args[0][0],
            {'qs': {'foo': 'bar'}})

    def test_callback_validation_failure(self):
        self.set_mocks({
            'provider.reference.notices': {
                'method': 'post',
                'return': {
                    'result': 'FAIL',
                    'reason': 'signature mismatch',
                }
            },
            'provider.reference.transactions': {
                'method': 'post',
                'return': {
                    'token': 'zippy-trans-token',
                }
            }},
            product_uuid='XYZ'
        )

        self.configure(seller_uuid='seller-xyz', product_uuid='app-xyz')
        is_valid = self.provider.is_callback_token_valid({'foo': 'bar'})
        eq_(is_valid, False)


class TestBoku(ProviderTestCase):

    def setUp(self):
        self.slumber = mock.MagicMock()
        self.provider = ProviderHelper('boku', slumber=self.slumber)

    def set_mocks(self, returns={}, keys=None, **kw):
        if not keys:
            keys = ('generic.seller',
                    'generic.product',
                    'generic.buyer',
                    'boku.transactions',)
        return super(TestBoku, self).set_mocks(
            returns=returns, keys=keys, **kw)

    def configure(self, **kw):
        kw.setdefault('mcc', mobile_codes.alpha2('MX').mcc)
        kw.setdefault('mnc', '020')  # AMX
        return super(TestBoku, self).configure(**kw)

    def test_start_transaction(self):
        seller_uuid = 'seller-xyz'
        user_uuid = 'user-xyz'

        self.set_mocks({
            'boku.transactions': {
                'method': 'post',
                'return': {
                    'buy_url': 'https://site/buy',
                    'transaction_id': 'boku-trans-id',
                }
            }},
            seller_uuid=seller_uuid,
            product_uuid='XYZ'
        )

        result = self.configure(seller_uuid=seller_uuid,
                                user_uuid=user_uuid)

        eq_(result[0], 'boku-trans-id')
        eq_(result[1], seller_uuid)

        kw = self.slumber.boku.transactions.post.call_args[0][0]
        eq_(kw['price'], '55.00')
        eq_(kw['country'], 'MX')
        eq_(kw['seller_uuid'], seller_uuid)
        eq_(kw['user_uuid'], user_uuid)
        assert 'transaction_uuid' in kw, 'Missing keys: {kw}'.format(kw=kw)
        assert self.slumber.generic.transaction.post.called

    @raises(BokuProvider.TransactionError)
    def test_unknown_network(self):
        self.configure(mcc=None, mnc=None)

    @raises(BokuProvider.TransactionError)
    def test_unknown_price(self):
        # Simulate when a network is mapped to a currency that doesn't exist.
        self.configure(prices=[])


@mock.patch('lib.solitude.api.client.slumber')
class TransactionTest(TestCase):

    def test_notes_transactions(self, slumber):
        slumber.generic.transaction.get_object.return_value = {
            'notes': json.dumps({'foo': 'bar'})
        }
        trans = client.get_transaction('x')
        eq_(trans['notes'], {'foo': 'bar'})


@mock.patch.object(settings, 'PAYMENT_PROVIDER', 'bango')
class TestProviderHelper(TestCase):

    def test_from_boku_operator(self):
        mcc = '334'  # Mexico
        mnc = '020'  # AMX

        provider = ProviderHelper.choose(mcc=mcc, mnc=mnc)
        eq_(provider.name, BokuProvider.name)

    def test_from_wrong_mexican_operator(self):
        mcc = '334'  # Mexico
        mnc = '03'  # Movistar

        provider = ProviderHelper.choose(mcc=mcc, mnc=mnc)
        eq_(provider.name, BangoProvider.name)

    def test_not_from_mexico(self):
        mcc = '214'  # Spain
        mnc = '01'  # Vodaphone

        provider = ProviderHelper.choose(mcc=mcc, mnc=mnc)
        eq_(provider.name, BangoProvider.name)

    def test_no_network(self):
        provider = ProviderHelper.choose()
        eq_(provider.name, BangoProvider.name)
