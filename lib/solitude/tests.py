import json

from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

import mobile_codes
import mock
from nose.tools import eq_, raises
from slumber.exceptions import HttpClientError

from lib.solitude.api import (BokuProvider, client,
                              ProviderHelper, SellerNotConfigured)
from lib.solitude.constants import ACCESS_PURCHASE
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

    @mock.patch('lib.utils.log')
    def test_invalid_json_response(self, fake_log, slumber):
        slumber.generic.buyer.get_object_or_404.side_effect = HttpClientError(
            response=self.create_error_response(content='<not valid json>'))
        with self.assertRaises(ValueError):
            client.get_buyer('catastrophic-non-json-error')
        assert fake_log.error.called, 'expected response to be logged'

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


class TestBango(TestCase):
    uuid = 'some:pin'
    seller = {'bango': {'seller': 's', 'resource_uri': 'r',
                        'package_id': '1234'},
              'resource_uri': '/seller/1',
              'resource_pk': 'seller_pk'}

    def setUp(self):
        super(TestBango, self).setUp()
        self.slumber = mock.MagicMock()
        self.provider = ProviderHelper('bango', slumber=self.slumber)

    def start(self):
        return self.provider.start_transaction(*range(0, 9))

    def test_create_without_bango_seller(self):
        self.slumber.generic.seller.get_object.return_value = {
            'bango': None, 'resource_pk': '1',
            'resource_uri': '/seller/1'
        }
        with self.assertRaises(ValueError):
            self.provider.create_product(
                external_id='ext:id', product_name='product name',
                generic_seller={},
                provider_seller_uuid='provider_seller_uuid',
                generic_product={'resource_pk': '2',
                                 'resource_uri': '/foo'})
        self.slumber.generic.seller.get_object.assert_called_with(
            uuid='provider_seller_uuid')

    def test_create_bango_product(self):
        slumber = self.slumber
        slumber.bango.generic.post.return_value = {'product': 'some:uri'}
        slumber.bango.product.post.return_value = {'resource_uri': 'some:uri',
                                                   'bango_id': '5678'}
        assert self.provider.create_product(
            external_id='ext:id', product_name='product:name',
            generic_seller=self.seller, provider_seller_uuid='xyz')
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
            self.start()

    def test_no_bango_product(self):
        slumber = self.slumber
        slumber.generic.seller.get_object_or_404.return_value = self.seller
        slumber.bango.billing.post.return_value = {
            'billingConfigurationId': 'bill_id'}
        slumber.bango.product.get_object_or_404.side_effect = (
            ObjectDoesNotExist)
        trans_id, pay_url, seller_uuid = self.start()
        eq_(trans_id, 'bill_id')

    def test_with_bango_product(self):
        slumber = self.slumber
        slumber.generic.seller.get_object_or_404.return_value = self.seller
        slumber.bango.billing.post.return_value = {
            'billingConfigurationId': 'bill_id'}
        slumber.bango.product.get_object.return_value = {
            'resource_uri': 'foo'}
        trans_id, pay_url, seller_uuid = self.start()
        eq_(trans_id, 'bill_id')

    def test_pay_url(self):
        bill_id = '123'
        slumber = self.slumber
        slumber.generic.seller.get_object_or_404.return_value = self.seller
        slumber.bango.billing.post.return_value = {
            'billingConfigurationId': bill_id}

        with self.settings(
            PAY_URLS={'bango': {'base': 'http://bango',
                                'pay': '/pay?bcid={uid_pay}'}}):
            trans_id, pay_url, seller_uuid = self.start()

        eq_(pay_url, 'http://bango/pay?bcid={b}'.format(b=bill_id))


class ProviderTestCase(TestCase):

    def configure(self, trans_uuid='trans-xyz', seller_uuid='seller-xyz',
                  product_uuid='product-xyz', product_name='Shiny App',
                  success_redirect='/todo/postback',
                  error_redirect='/todo/chargeback',
                  provider_seller_uuid='provider-sel-xyz',
                  prices=[{'price': '0.89', 'currency': 'EUR', 'region': 14},
                          {'price': '55.00', 'currency': 'MXN', 'region': 12}],
                  icon_url='/todo/icons', user_uuid='user-xyz',
                  app_size=1024 * 5, mcc=None, mnc=None):
        return self.provider.start_transaction(
            transaction_uuid=trans_uuid,
            generic_seller_uuid=seller_uuid,
            provider_seller_uuid=provider_seller_uuid,
            product_id=product_uuid,
            product_name=product_name,
            prices=prices,
            icon_url=icon_url,
            user_uuid=user_uuid,
            application_size=app_size,
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

        Here's an example of mocking a side effect when calling post():

            self.set_mocks({
                'provider.reference.transactions': {
                    'method': 'post',
                    'side_effect': ValueError,
                }
            })

        * If no method is specified, the default is get_object_or_404.
        * If no return is specified, the return will be a resource_pk, uuid,
          and resource_uri
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


class TestReferenceProvider(ProviderTestCase):

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
        return super(TestReferenceProvider, self).set_mocks(
            returns=returns, keys=keys, **kw)

    def test_start_with_existing_prod(self):
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

        trans_id, pay_url, seller_uuid = self.configure(
            seller_uuid=seller_uuid, product_uuid=product_uuid)

        eq_(trans_id, 'zippy-trans-token')
        eq_(seller_uuid, seller_uuid)
        assert pay_url.endswith('tx={t}'.format(t=trans_id)), (
            'Unexpected: {url}'.format(url=pay_url))

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
        provider_seller_uuid = 'provider-sel-xyz'
        user_uuid = 'user-xyz'
        boku_pay_url = 'https://site/buy'

        self.set_mocks({
            'boku.transactions': {
                'method': 'post',
                'return': {
                    'buy_url': boku_pay_url,
                    'transaction_id': 'boku-trans-id',
                }
            }},
            seller_uuid=seller_uuid,
            product_uuid='XYZ'
        )

        trans_id, pay_url, seller_uuid = self.configure(
            seller_uuid=seller_uuid, user_uuid=user_uuid,
            provider_seller_uuid=provider_seller_uuid)

        eq_(trans_id, 'boku-trans-id')
        eq_(pay_url, boku_pay_url)

        kw = self.slumber.boku.transactions.post.call_args[0][0]
        eq_(kw['price'], '55.00')
        eq_(kw['country'], 'MX')
        eq_(kw['seller_uuid'], provider_seller_uuid)
        eq_(kw['user_uuid'], user_uuid)
        assert kw['callback_url'].endswith(reverse('provider.notification',
                                                   args=['boku'])), (
            'Unexpected: {u}'.format(u=kw['callback_url']))
        assert kw['forward_url'].endswith(reverse('provider.wait_to_finish',
                                                  args=['boku'])), (
            'Unexpected: {u}'.format(u=kw['forward_url']))
        assert 'transaction_uuid' in kw, 'Missing keys: {kw}'.format(kw=kw)
        assert self.slumber.generic.transaction.post.called

    def test_new_inapp_transaction(self):
        seller_uuid = 'seller-xyz'
        external_id = 'external-id'
        boku_pay_url = 'https://site/buy'

        self.set_mocks({
            # Return a 404 as if this is the first purchase
            # for the in-app product.
            'generic.product': {
                'method': 'get_object_or_404',
                'side_effect': ObjectDoesNotExist,
            },
            'boku.transactions': {
                'method': 'post',
                'return': {
                    'buy_url': boku_pay_url,
                    'transaction_id': 'boku-trans-id',
                }
            }},
            seller_uuid=seller_uuid,
            product_uuid='XYZ')

        trans_id, pay_url, seller_uuid = self.configure(
            seller_uuid=seller_uuid, product_uuid=external_id)

        # Make sure the new in-app product was created.
        kw = self.slumber.generic.product.post.call_args[0][0]
        eq_(kw['external_id'], external_id)
        eq_(kw['seller'], '/seller/{u}'.format(u=seller_uuid))
        eq_(kw['access'], ACCESS_PURCHASE)

        assert self.slumber.boku.transactions.post.called
        assert self.slumber.generic.transaction.post.called

    @raises(BokuProvider.TransactionError)
    def test_unknown_network(self):
        self.configure(mcc=None, mnc=None)

    @raises(BokuProvider.TransactionError)
    def test_unknown_price(self):
        # Simulate when a network is mapped to a currency that doesn't exist.
        self.configure(prices=[])

    def test_transaction_from_notice(self):
        trans_uuid = '123'
        qs = {'param': trans_uuid}
        eq_(self.provider.provider.transaction_from_notice(qs),
            trans_uuid)

    def test_no_transaction_from_notice(self):
        eq_(self.provider.provider.transaction_from_notice({}), None)


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

    def test_supported_providers_returns_default_provider(self):
        providers = ProviderHelper.supported_providers()
        eq_(len(providers), 1)

        provider = providers[0]
        eq_(provider.name, settings.PAYMENT_PROVIDER)

    def test_from_boku_operator(self):
        mcc = '334'  # Mexico
        mnc = '020'  # AMX

        providers = ProviderHelper.supported_providers(mcc=mcc, mnc=mnc)
        provider_names = [provider.name for provider in providers]
        eq_(provider_names, [
            BokuProvider.name, settings.PAYMENT_PROVIDER])

    def test_from_wrong_mexican_operator(self):
        mcc = '334'  # Mexico
        mnc = '03'  # Movistar

        providers = ProviderHelper.supported_providers(mcc=mcc, mnc=mnc)
        provider_names = [provider.name for provider in providers]
        eq_(provider_names, [settings.PAYMENT_PROVIDER])

    def test_not_from_mexico(self):
        mcc = '214'  # Spain
        mnc = '01'  # Vodaphone

        providers = ProviderHelper.supported_providers(mcc=mcc, mnc=mnc)
        provider_names = [provider.name for provider in providers]
        eq_(provider_names, [settings.PAYMENT_PROVIDER])
