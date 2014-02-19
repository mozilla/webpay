import json
import logging
import uuid
import warnings

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse

from slumber.exceptions import HttpClientError
from webpay.base.helpers import absolutify

from ..utils import SlumberWrapper
from . import constants as solitude_const
from .errors import ERROR_STRINGS
from .exceptions import ResourceNotModified


log = logging.getLogger('w.solitude')
client = None


class SellerNotConfigured(Exception):
    """The seller has not yet been configued for the payment."""


class SolitudeAPI(SlumberWrapper):
    """
    A Solitude API that connects to the universal payment provider API.

    :param url: URL of the solitude endpoint.
    """
    errors = ERROR_STRINGS

    def __init__(self, *args, **kw):
        super(SolitudeAPI, self).__init__(*args, **kw)
        self._provider = None

    @property
    def provider(self):
        assert self._provider, 'self._provider has not been set'
        return getattr(self.slumber.provider, self._provider)

    def set_provider(self, provider=None):
        self._provider = provider or settings.PAYMENT_PROVIDER
        return self._provider

    def create_buyer(self, uuid, pin=None):
        """Creates a buyer with an optional PIN in solitude.

        :param uuid: String to identify the buyer by.
        :param pin: Optional PIN that will be hashed.
        :rtype: dictionary
        """
        obj = self.safe_run(self.slumber.generic.buyer.post,
                            {'uuid': uuid, 'pin': pin})
        if 'etag' in obj:
            etag = obj['etag']
            cache.set('etag:%s' % uuid, etag)
            cache.set('buyer:%s' % etag, obj)
        return obj

    def get_buyer(self, uuid, use_etags=True):
        """Retrieves a buyer by their uuid.

        :param uuid: String to identify the buyer by.
        :rtype: dictionary
        """
        cache_key = 'etag:%s' % uuid
        etag = cache.get(cache_key) if use_etags else None
        headers = {'If-None-Match': etag} if etag else {}
        try:
            obj = self.safe_run(self.slumber.generic.buyer.get_object_or_404,
                                headers=headers, uuid=uuid)
        except ResourceNotModified:
            return (cache.get('buyer:%s' % etag)
                    or self.get_buyer(uuid, use_etags=False))
        except ObjectDoesNotExist:
            obj = {}
        if 'etag' in obj:
            etag = obj['etag']
            cache.set(cache_key, etag)
            cache.set('buyer:%s' % etag, obj)
        return obj

    def set_needs_pin_reset(self, uuid, value=True, etag=''):
        """Set flag for user to go through reset flow or not on next log in.

        :param uuid: String to identify the buyer by.
        :param value: Boolean for whether they should go into the reset flow or
                      not, defaults to True
        :rtype: dictionary
        """
        id_ = self.get_buyer(uuid).get('resource_pk')
        res = self.safe_run(self.slumber.generic.buyer(id=id_).patch,
                            {'needs_pin_reset': value, 'new_pin': None},
                            headers={'If-Match': etag})
        if 'errors' in res:
            return res
        return {}

    def unset_was_locked(self, uuid, etag=''):
        """Unsets the flag to view the was_locked screen.

        :param uuid: String to identify the buyer by.
        :rtype: dictionary
        """
        id_ = self.get_buyer(uuid).get('resource_pk')
        res = self.safe_run(self.slumber.generic.buyer(id=id_).patch,
                            {'pin_was_locked_out': False},
                            headers={'If-Match': etag})
        if 'errors' in res:
            return res
        return {}

    def change_pin(self, uuid, pin, etag=''):
        """Changes the pin of a buyer, for use with buyers who exist without
        pins.

        :param buyer_id integer: ID of the buyer you'd like to change the PIN
                                 for.
        :param pin: PIN the user would like to change to.
        :rtype: dictionary
        """
        id_ = self.get_buyer(uuid).get('resource_pk')
        res = self.safe_run(self.slumber.generic.buyer(id=id_).patch,
                            {'pin': pin},
                            headers={'If-Match': etag})
        # Empty string is a good thing from tastypie for a PATCH.
        if 'errors' in res:
            return res
        return {}

    def set_new_pin(self, uuid, new_pin, etag=''):
        """Sets the new_pin for use with a buyer that is resetting their pin.

        :param buyer_id integer: ID of the buyer you'd like to change the PIN
                                 for.
        :param pin: PIN the user would like to change to.
        :rtype: dictionary
        """
        id_ = self.get_buyer(uuid).get('resource_pk')
        res = self.safe_run(self.slumber.generic.buyer(id=id_).patch,
                            {'new_pin': new_pin},
                            headers={'If-Match': etag})
        # Empty string is a good thing from tastypie for a PATCH.
        if 'errors' in res:
            return res
        return {}

    def get_active_product(self, public_id):
        """
        Retrieves a an active seller product by its public_id.

        :param public_id: Product public_id.
        :rtype: dictionary
        """
        return self.slumber.generic.product.get_object_or_404(
            seller__active=True, public_id=public_id)

    def confirm_pin(self, uuid, pin):
        """Confirms the buyer's pin, marking it at confirmed in solitude

        :param uuid: String to identify the buyer by.
        :param pin: PIN to confirm
        :rtype: boolean
        """

        res = self.safe_run(self.slumber.generic.confirm_pin.post,
                            {'uuid': uuid, 'pin': pin})
        return res.get('confirmed', False)

    def reset_confirm_pin(self, uuid, pin):
        """Confirms the buyer's pin, marking it at confirmed in solitude

        :param uuid: String to identify the buyer by.
        :param pin: PIN to confirm
        :rtype: boolean
        """

        res = self.safe_run(self.slumber.generic.reset_confirm_pin.post,
                            {'uuid': uuid, 'pin': pin})
        return res.get('confirmed', False)

    def verify_pin(self, uuid, pin):
        """Checks the buyer's PIN against what is stored in solitude.

        :param uuid: String to identify the buyer by.
        :param pin: PIN to check
        :rtype: dictionary
        """

        res = self.safe_run(self.slumber.generic.verify_pin.post,
                            {'uuid': uuid, 'pin': pin})
        return res

    def configure_product_for_billing(self, transaction_uuid,
                                      seller_uuid,
                                      product_id, product_name,
                                      prices, icon_url,
                                      user_uuid, application_size,
                                      source='unknown',
                                      provider=None):
        """
        Start a payment provider transaction to begin the purchase flow.

        TODO(Kumar): rename this function when we no longer need to
        maintain the Bango one.
        """
        provider = self.set_provider(provider)
        try:
            seller = self.slumber.generic.seller.get_object_or_404(
                                                    uuid=seller_uuid)
        except ObjectDoesNotExist:
            raise SellerNotConfigured('Seller with uuid %s does not exist'
                                      % seller_uuid)
        seller_id = seller['resource_pk']
        log.info('transaction %s: seller: %s' % (transaction_uuid,
                                                 seller_id))
        log.info('{provider}: get product for '
                 'seller_uuid={uuid} external_id={ext}'
                 .format(provider=provider,
                         uuid=seller_uuid, ext=product_id))

        product = None
        try:
            product = self.slumber.generic.product.get_object_or_404(
                external_id=product_id,
                seller=seller_id,
            )
            log.info('found product {pr}'.format(pr=product))
            provider_product = self.provider.products.get_object_or_404(
                                                seller_id=seller_uuid,
                                                external_id=product_id)
            log.info('found provider product {pr}'.format(pr=provider_product))
        except ObjectDoesNotExist:
            product, provider_product = self.create_product(
                                product_id, product_name,
                                seller, provider=provider,
                                generic_product=product)

        # TODO: Make these real values. See bug 941952.
        carrier = 'USA_TMOBILE'
        region = '123'
        pay_method = 'OPERATOR'
        price = '0.99'
        currency = 'EUR'

        provider_trans = self.provider.transactions.post({
            'product_id': provider_product['resource_pk'],
            'region': region,
            'carrier': carrier,
            'price': price,
            'currency': currency,
            'pay_method': pay_method,
            'callback_success_url': absolutify(
                                        reverse('pay.callback_success_url')),
            'callback_error_url': absolutify(
                                        reverse('pay.callback_error_url')),
            'ext_transaction_id': transaction_uuid,
            'success_url': absolutify(reverse('provider.success',
                                      args=[provider])),
            'error_url': absolutify(reverse('provider.error',
                                    args=[provider])),
            'product_image_url': icon_url,
        })
        log.info('made provider trans {trans}'.format(trans=provider_trans))

        # Note that the old Bango code used to do get-or-create
        # but I can't tell if we need that or not. Let's wait until it breaks.
        # See solitude/lib/transactions/models.py
        trans = self.slumber.generic.transaction.post({
            'uuid': transaction_uuid,
            'status': solitude_const.STATUS_PENDING,
            'provider': solitude_const.PROVIDERS[provider],
            'seller_product': product['resource_uri'],
            'source': solitude_const.PROVIDERS[provider],
            'region': region,
            'carrier': carrier,
            'type': solitude_const.TYPE_PAYMENT,
            'amount': price,
            'currency': currency,
        })
        log.info('made solitude trans {trans}'.format(trans=trans))

        return provider_trans['token'], seller_id

    def create_product(self, external_id, product_name, generic_seller,
                       provider=None, generic_product=None):
        """
        Creates a generic product and provider product on the fly.

        This is for scenarios like adhoc in-app payments where the
        system might be selling a product for the first time.
        """
        provider = self.set_provider(provider)

        log.info(('creating product with name: {name}, '
                  'external_id: {ext_id}, seller: {seller}')
                  .format(name=product_name, ext_id=external_id,
                          seller=generic_seller))

        if not generic_product:
            generic_product = self.slumber.generic.product.post({
                'external_id': external_id,
                'seller': generic_seller['resource_uri'],
                'public_id': str(uuid.uuid4()),
                'access': solitude_const.ACCESS_PURCHASE,
            })
            log.info('created generic product {pr}'
                     .format(pr=generic_product))

        # If there is no provider seller it means the billing account has
        # not yet been set up in Devhub.
        provider_seller = self.provider.sellers.get_object_or_404(
                                        uuid=generic_seller['resource_pk'])

        provider_product = self.provider.products.post({
            'external_id': external_id,
            'seller_id': provider_seller['resource_pk'],
            'name': product_name,
        })
        log.info('created provider product {pr}'
                 .format(pr=provider_product))

        return generic_product, provider_product

    def get_transaction(self, uuid):
        transaction = self.slumber.generic.transaction.get_object(uuid=uuid)
        # Notes may contain some JSON, including the original pay request.
        notes = transaction['notes']
        if notes:
            transaction['notes'] = json.loads(notes)
        return transaction

    def is_callback_token_valid(self, querystring, provider=None):
        provider = self.set_provider(provider)
        try:
            response = self.provider.notices.post({'qs': querystring})
        except HttpClientError as e:
            log.error(('Notice creation with querystring {querystring} failed:'
                       ' {error}').format(querystring=querystring, error=e))
            return False
        log.info('validation of the token against the provider {response}'
                 .format(response=response))
        return response['result'] == 'OK'


class BangoSolitudeAPI(SolitudeAPI):
    """
    DEPRECATED Solitude API that connects to Bango directly.

    :param url: URL of the solitude endpoint.
    """

    def configure_product_for_billing(self, transaction_uuid,
                                      seller_uuid,
                                      product_id, product_name,
                                      prices, icon_url,
                                      user_uuid, application_size,
                                      source='unknown'):
        """
        Get the billing configuration ID for a Bango transaction.
        """

        # TODO: remove this.
        # Do not edit this code. Add new logic to the SolitudeAPI.

        redirect_url_onsuccess = absolutify(reverse('bango.success'))
        redirect_url_onerror = absolutify(reverse('bango.error'))

        try:
            seller = self.slumber.generic.seller.get_object_or_404(
                uuid=seller_uuid)
        except ObjectDoesNotExist:
            raise SellerNotConfigured('Seller with uuid %s does not exist'
                                      % seller_uuid)
        seller_id = seller['resource_pk']
        log.info('transaction %s: seller: %s' % (transaction_uuid,
                                                 seller_id))

        try:
            bango_product = self.slumber.bango.product.get_object_or_404(
                seller_product__seller=seller_id,
                seller_product__external_id=product_id)
        except ObjectDoesNotExist:
            bango_product = self.create_product(product_id, product_name,
                                                seller)

        log.info('transaction %s: bango product: %s'
                 % (transaction_uuid, bango_product['resource_uri']))

        res = self.slumber.bango.billing.post({
            'pageTitle': product_name,
            'prices': prices,
            'transaction_uuid': transaction_uuid,
            'seller_product_bango': bango_product['resource_uri'],
            'redirect_url_onsuccess': redirect_url_onsuccess,
            'redirect_url_onerror': redirect_url_onerror,
            'icon_url': icon_url,
            'user_uuid': user_uuid,
            'application_size': application_size,
            'source': source
        })
        bill_id = res['billingConfigurationId']
        log.info('transaction %s: billing config ID: %s; '
                 'prices: %s'
                 % (transaction_uuid, bill_id, prices))

        return bill_id, seller_id

    def create_product(self, external_id, product_name, seller):
        """
        Creates a product and a Bango ID on the fly in solitude.
        """

        # TODO: remove this.
        # Do not edit this code. Add new logic to the SolitudeAPI.

        log.info(('creating product with  name: %s, external_id: %s , '
                  'seller: %s') % (product_name, external_id, seller))
        if not seller['bango']:
            raise ValueError('No bango account set up for %s' %
                             seller['resource_pk'])

        product = self.slumber.generic.product.post({
            'external_id': external_id,
            'seller': seller['bango']['seller'],
            'public_id': str(uuid.uuid4()),
            'access': solitude_const.ACCESS_PURCHASE,
        })
        bango = self.slumber.bango.product.post({
            'seller_bango': seller['bango']['resource_uri'],
            'seller_product': product['resource_uri'],
            'name': product_name,
            'categoryId': 1,
            'packageId': seller['bango']['package_id'],
            'secret': 'n'  # This is likely going to be removed.
        })
        self.slumber.bango.premium.post({
            'bango': bango['bango_id'],
            'seller_product_bango': bango['resource_uri'],
            # TODO(Kumar): why do we still need this?
            # The array of all possible prices/currencies is
            # set in the configure billing call.
            # Marketplace also sets dummy prices here.
            'price': '0.99',
            'currencyIso': 'USD',
        })

        self.slumber.bango.rating.post({
            'bango': bango['bango_id'],
            'rating': 'UNIVERSAL',
            'ratingScheme': 'GLOBAL',
            'seller_product_bango': bango['resource_uri']
        })
        # Bug 836865.
        self.slumber.bango.rating.post({
            'bango': bango['bango_id'],
            'rating': 'GENERAL',
            'ratingScheme': 'USA',
            'seller_product_bango': bango['resource_uri']
        })

        return bango


if not settings.SOLITUDE_URL:
    # This will typically happen when Sphinx builds the docs.
    warnings.warn('SOLITUDE_URL not found, not setting up client')
    client = None
else:
    args = (settings.SOLITUDE_URL, settings.SOLITUDE_OAUTH)
    if settings.UNIVERSAL_PROVIDER:
        log.info('Using universal SolitudeAPI')
        client = SolitudeAPI(*args)
    else:
        log.info('Using BangoSolitudeAPI')
        client = BangoSolitudeAPI(*args)
