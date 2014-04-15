import json
import logging
import uuid
import warnings

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse

import mobile_codes
from slumber.exceptions import HttpClientError
from webpay.base import dev_messages as msg
from webpay.base.helpers import absolutify

from lib.marketplace.constants import COUNTRIES
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
    A Solitude facade that works with a payment provider or the
    generic Solitude API.

    :param url: URL of the solitude endpoint.
    """
    errors = ERROR_STRINGS

    def __init__(self, *args, **kw):
        super(SolitudeAPI, self).__init__(*args, **kw)

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

    def get_transaction(self, uuid):
        transaction = self.slumber.generic.transaction.get_object(uuid=uuid)
        # Notes may contain some JSON, including the original pay request.
        notes = transaction['notes']
        if notes:
            transaction['notes'] = json.loads(notes)
        return transaction


class ProviderHelper:
    """
    A common interface to all payment providers.
    """
    def __init__(self, name, slumber=None):
        self.slumber = slumber or client.slumber
        ProviderClass = provider_cls(name)
        self.provider = ProviderClass(self.slumber)
        self.name = self.provider.name

    @classmethod
    def choose(cls, mcc=None, mnc=None):
        """
        Given the user's mobile network (when available) return a suitable
        provider helper object.

        Keyword arguments:

        **mcc**
            The user's mobile carrier code, if known.

        **mnc**
            The user's mobile network code, if known.
        """
        # Switch to Boku when on one of their networks.
        if (mcc, mnc) in BokuProvider.network_data:
            provider_name = BokuProvider.name
        else:
            provider_name = settings.PAYMENT_PROVIDER

        log.info('choosing payment provider "{pr}" for mcc {mcc}, mnc {mnc}'
                 .format(pr=provider_name, mcc=mcc, mnc=mnc))

        # TODO: fall back to a payment provider *supported* by the
        # seller. bug 993691.

        return cls(provider_name)

    def start_transaction(self, transaction_uuid,
                          seller_uuid,
                          product_id, product_name,
                          prices, icon_url,
                          user_uuid, application_size,
                          source='unknown',
                          mcc=None, mnc=None):
        """
        Start a payment provider transaction to begin the purchase flow.
        """
        try:
            seller = self.slumber.generic.seller.get_object_or_404(
                uuid=seller_uuid)
        except ObjectDoesNotExist:
            raise SellerNotConfigured(
                '{pr}: Seller with uuid {u} does not exist'
                .format(u=seller_uuid, pr=self.provider.name))
        seller_id = seller['resource_pk']
        log.info('{pr}: transaction {tr}: seller: {sel}'
                 .format(tr=transaction_uuid, sel=seller_id,
                         pr=self.provider.name))
        log.info('{pr}: get product for seller_uuid={uuid} external_id={ext}'
                 .format(pr=self.provider.name,
                         uuid=seller_uuid, ext=product_id))

        product = None
        try:
            product = self.slumber.generic.product.get_object_or_404(
                external_id=product_id,
                seller=seller_id,
            )
            log.info('{pr}: found generic product {prod}'
                     .format(pr=self.provider.name, prod=product))
            provider_product = self.provider.get_product(seller, product)
            log.info('{pr}: found provider product {prod}'
                     .format(prod=provider_product, pr=self.provider.name))
        except ObjectDoesNotExist:
            product, provider_product = self.create_product(
                product_id, product_name,
                seller, generic_product=product)

        trans_token, pay_url = self.provider.create_transaction(
            generic_seller=seller,
            generic_product=product,
            provider_product=provider_product,
            product_name=product_name,
            transaction_uuid=transaction_uuid,
            prices=prices,
            user_uuid=user_uuid,
            application_size=application_size,
            source=source,
            icon_url=icon_url,
            mcc=mcc,
            mnc=mnc,
        )
        log.info('{pr}: made provider trans {trans}'
                 .format(trans=trans_token, pr=self.provider.name))

        return trans_token, pay_url, seller_id

    def create_product(self, external_id, product_name, generic_seller,
                       generic_product=None):
        """
        Creates a generic product and provider product on the fly.

        This is for scenarios like adhoc in-app payments where the
        system might be selling a product for the first time.
        """
        log.info('{pr}: creating product with name: {name}, '
                 'external_id: {ext_id}, seller: {seller}'
                 .format(name=product_name, ext_id=external_id,
                         seller=generic_seller,
                         pr=self.provider.name))

        if not generic_product:
            generic_product = self.slumber.generic.product.post({
                'external_id': external_id,
                'seller': generic_seller['resource_uri'],
                'public_id': str(uuid.uuid4()),
                'access': solitude_const.ACCESS_PURCHASE,
            })
            log.info('{pr}: created generic product {prod}'
                     .format(prod=generic_product, pr=self.provider.name))

        # If there is no provider seller it means the billing account has
        # not yet been set up in Devhub. Thus, we're not caching an exception
        # here.
        provider_seller = self.provider.get_seller(generic_seller)

        provider_product = self.provider.create_product(
            generic_product, provider_seller, external_id, product_name)
        log.info('{pr}: created provider product {prod}'
                 .format(prod=provider_product, pr=self.provider.name))

        return generic_product, provider_product

    def is_callback_token_valid(self, querystring):
        try:
            response = self.provider.create_notice(querystring)
        except HttpClientError as e:
            log.error('{pr}: Notice creation with querystring {querystring} '
                      'failed: {error}'
                      .format(querystring=querystring, error=e,
                              pr=self.provider.name))
            return False
        log.info('{pr}: validation of the token against the provider '
                 '{response}'.format(response=response,
                                     pr=self.provider.name))
        return response['result'] == 'OK'

    def prepare_notice(self, request):
        qs = request.GET
        if request.GET:
            raw_qs = request.get_full_path().split('?')[1]
        else:
            raw_qs = ''

        trans_id = self.provider.transaction_from_notice(qs)
        session_trans_id = request.session.get('trans_id')

        if not trans_id:
            log.info('Provider={pr} did not provide a transaction ID '
                     'on the query string'.format(pr=self.name))
            raise msg.DevMessage(msg.TRANS_MISSING)
        if trans_id != session_trans_id:
            log.info('Provider={pr} transaction {tr} is not in the '
                     'active session'.format(pr=self.name, tr=trans_id))
            raise msg.DevMessage(msg.NO_ACTIVE_TRANS)

        try:
            response = self.provider.get_notice_result(qs, raw_qs)
        except HttpClientError, err:
            log.error('post to reference payment notice for transaction '
                      'ID {trans} failed: {err}'
                      .format(trans=trans_id, err=err))
            raise msg.DevMessage(msg.NOTICE_EXCEPTION)

        log.info('reference payment notice check result={result}; '
                 'trans_id={trans}'.format(trans=trans_id,
                                           result=response['result']))

        if response['result'] != 'OK':
            raise msg.DevMessage(msg.NOTICE_ERROR)

        return trans_id

    def server_notification(self, request):
        """
        Handles the server to server notification that is sent after
        a transaction is completed.
        """
        # Get the notification data from the incoming request.
        data = self.provider.get_notification_data(request)

        try:
            # Post the result to solitude.
            self.provider.get_notification_result(data)
        except HttpClientError, err:
            log.error('Provider={pr} post failed: {err}'
                      .format(pr=self.name, err=err))
            raise msg.DevMessage(msg.NOTICE_ERROR)


_registry = {}


def provider_cls(name):
    return _registry[name]


def register_provider(cls):
    _registry[cls.name] = cls
    return cls


class PayProvider:
    """
    Abstract payment provider

    This encapsulates some API logic specific to payment providers
    such as configuring a new payment, creating products, etc.
    """
    name = None

    def __init__(self, slumber):
        self.slumber = slumber

    @property
    def api(self):
        # This gets a connection to the actual provider API
        # such as /provider/reference/:
        return getattr(self.slumber.provider, self.name)

    def get_product(self, generic_seller, generic_product):
        return self.api.products.get_object_or_404(
            seller_id=generic_seller['uuid'],
            external_id=generic_product['external_id'])

    def create_product(self, generic_product, provider_seller, external_id,
                       product_name):
        return self.api.products.post({
            'external_id': external_id,
            'seller_id': provider_seller['resource_pk'],
            'name': product_name,
        })

    def get_seller(self, generic_seller):
        return self.api.sellers.get_object_or_404(
            uuid=generic_seller['resource_pk'])

    def create_transaction(self, generic_seller, generic_product,
                           provider_product, product_name, transaction_uuid,
                           prices, user_uuid, application_size, source,
                           icon_url, mcc=None, mnc=None):
        """
        Create a provider specific transaction and a generic Solitude
        transaction.

        Return the provider a tuple of:

        (transaction ID, payment start URL)
        """
        raise NotImplementedError()

    def create_notice(self, querystring):
        return self.api.notices.post({'qs': querystring})

    def transaction_from_notice(self, parsed_qs):
        return parsed_qs.get('ext_transaction_id')

    def get_notice_result(self, parsed_qs, raw_qs):
        return self.api.notices.post({'qs': raw_qs})

    def get_notification_data(self, request):
        raise NotImplementedError

    def get_notification_result(self, data):
        return NotImplementedError

    def _formatted_payment_url(self, transaction_uuid):
        """Return a URL from a template using the transaction ID."""
        config = settings.PAY_URLS[self.name]
        return config['base'] + config['pay'].format(uid_pay=transaction_uuid)


@register_provider
class ReferenceProvider(PayProvider):
    """
    A reference payment provider

    Our current reference implementation is known as Zippy.

    This is our ideal API. If possible, other payment providers
    should follow this API.

    If this provider is fully compliant it probably shouldn't need
    to override any of the inherited methods.
    """
    name = 'reference'

    def create_transaction(self, generic_seller, generic_product,
                           provider_product, product_name, transaction_uuid,
                           prices, user_uuid, application_size, source,
                           icon_url, mcc=None, mnc=None):

        # TODO: Maybe make these real values. See bug 941952.
        # In the case of Zippy, it does not detect any of these values
        # itself. All other providers will detect these values without
        # help from Webpay.
        carrier = 'USA_TMOBILE'
        region = '123'
        pay_method = 'OPERATOR'
        # Note: most providers will use the prices array.
        price = '0.99'
        currency = 'EUR'

        provider_trans = self.api.transactions.post({
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
                                      args=[self.name])),
            'error_url': absolutify(reverse('provider.error',
                                    args=[self.name])),
            'product_image_url': icon_url,
        })

        # Note that the old Bango code used to do get-or-create
        # but I can't tell if we need that or not. Let's wait until it breaks.
        # See solitude/lib/transactions/models.py
        trans = self.slumber.generic.transaction.post({
            'uuid': transaction_uuid,
            'status': solitude_const.STATUS_PENDING,
            'provider': solitude_const.PROVIDERS[self.name],
            'seller_product': generic_product['resource_uri'],
            'source': solitude_const.PROVIDERS[self.name],
            'region': region,
            'carrier': carrier,
            'type': solitude_const.TYPE_PAYMENT,
            'amount': price,
            'currency': currency,
        })
        log.info('made solitude trans {trans}'.format(trans=trans))

        token = provider_trans['token']
        return token, self._formatted_payment_url(token)


@register_provider
class BokuProvider(PayProvider):
    """
    The Boku payment provider.
    """
    name = 'boku'
    # Boku has specific data associated with its supported networks.
    network_data = {
        # MCC, MNC
        # Mexico + AMX
        ('334', '020'): {'currency': 'MXN'},
    }

    class TransactionError(Exception):
        """Error relating to a Boku transaction."""

    @property
    def api(self):
        return self.slumber.boku

    def get_product(self, generic_seller, generic_product):
        # Boku doesn't have products. I think.
        return None

    def create_product(self, generic_product, provider_seller, external_id,
                       product_name):
        # Boku doesn't have products. I think.
        return None

    def get_seller(self, generic_seller):
        raise NotImplementedError()

    def create_transaction(self, generic_seller, generic_product,
                           provider_product, product_name, transaction_uuid,
                           prices, user_uuid, application_size, source,
                           icon_url, mcc=None, mnc=None):
        # This is a temporary hack, because it will try and do
        # network data on None and then fail.
        if settings.MCC_OVERRIDE:
            log.warning('MCC changed from {0} to {1} because of MCC_OVERRIDE'.
                        format(mcc, settings.MCC_OVERRIDE))
            mcc = settings.MCC_OVERRIDE

        if settings.MNC_OVERRIDE:
            log.warning('MNC changed from {0} to {1} because of MNC_OVERRIDE'.
                        format(mnc, settings.MNC_OVERRIDE))
            mnc = settings.MNC_OVERRIDE

        try:
            data = self.network_data[(mcc, mnc)]
        except KeyError:
            raise self.TransactionError('Unknown network: mcc={mcc}; mnc={mnc}'
                                        .format(mcc=mcc, mnc=mnc))
        country = mobile_codes.mcc(mcc)
        # TODO: consider using get_price_country here?
        marketplace_country = COUNTRIES[mcc]
        price = None
        for pr in prices:
            # Given a list of all prices + currencies for this price point,
            # send Boku the one that matches the user's network.
            if pr['region'] == marketplace_country:
                price = pr['price']
                break
        if not price:
            raise self.TransactionError(
                'Could not find a price for region: mcc={mcc}; mnc={mnc}'
                .format(mcc=mcc, mnc=mnc))

        provider_trans = self.api.transactions.post({
            'callback_url': absolutify(reverse('provider.success',
                                               args=[self.name])),
            'country': country.alpha2,
            # TODO: figure out error callbacks in bug 987843.
            #'error_url': absolutify(reverse('provider.error',
            #                                args=[self.name])),
            'price': price,
            'seller_uuid': generic_seller['uuid'],
            'transaction_uuid': transaction_uuid,
            'user_uuid': user_uuid,
        })
        log.info('{pr}: made provider trans {trans}'
                 .format(pr=self.name, trans=provider_trans))

        trans = self.slumber.generic.transaction.post({
            'provider': solitude_const.PROVIDERS[self.name],
            'seller_product': generic_product['resource_uri'],
            'source': solitude_const.PROVIDERS[self.name],
            'status': solitude_const.STATUS_PENDING,
            'type': solitude_const.TYPE_PAYMENT,
            'uuid': transaction_uuid,
        })
        log.info('{pr}: made solitude trans {trans}'
                 .format(pr=self.name, trans=trans))

        return provider_trans['transaction_id'], provider_trans['buy_url']

    def get_notification_data(self, request):
        return request.GET

    def get_notification_result(self, data):
        return self.api.event.post(data)


@register_provider
class BangoProvider(PayProvider):
    """
    Bango payment provider
    """
    name = 'bango'

    @property
    def api(self):
        return self.slumber.bango

    def get_product(self, generic_seller, generic_product):
        return self.api.product.get_object_or_404(
            seller_product__seller=generic_seller['resource_pk'],
            seller_product__external_id=generic_product['external_id'])

    def create_product(self, generic_product, provider_seller, external_id,
                       product_name):
        bango_product = self.api.product.post({
            'seller_bango': provider_seller['resource_uri'],
            'seller_product': generic_product['resource_uri'],
            'name': product_name,
            'categoryId': 1,
            'packageId': provider_seller['package_id'],
            'secret': 'n'  # This is likely going to be removed.
        })
        self.api.premium.post({
            'bango': bango_product['bango_id'],
            'seller_product_bango': bango_product['resource_uri'],
            # TODO(Kumar): why do we still need this?
            # The array of all possible prices/currencies is
            # set in the configure billing call.
            # Marketplace also sets dummy prices here.
            'price': '0.99',
            'currencyIso': 'USD',
        })

        self.api.rating.post({
            'bango': bango_product['bango_id'],
            'rating': 'UNIVERSAL',
            'ratingScheme': 'GLOBAL',
            'seller_product_bango': bango_product['resource_uri']
        })
        # Bug 836865.
        self.api.rating.post({
            'bango': bango_product['bango_id'],
            'rating': 'GENERAL',
            'ratingScheme': 'USA',
            'seller_product_bango': bango_product['resource_uri']
        })

        return bango_product

    def get_seller(self, generic_seller):
        if not generic_seller['bango']:
            raise ValueError('No bango account set up for {sel}'
                             .format(sel=generic_seller['resource_pk']))
        return generic_seller['bango']

    def create_transaction(self, generic_seller, generic_product,
                           provider_product, product_name, transaction_uuid,
                           prices, user_uuid, application_size, source,
                           icon_url, mcc=None, mnc=None):
        log.info('transaction {tr}: bango product: {pr}'
                 .format(tr=transaction_uuid,
                         pr=provider_product['resource_uri']))

        redirect_url_onsuccess = absolutify(reverse('bango.success'))
        redirect_url_onerror = absolutify(reverse('bango.error'))

        # This API call also creates a generic
        # transaction automatically.
        res = self.api.billing.post({
            'pageTitle': product_name,
            'prices': prices,
            'transaction_uuid': transaction_uuid,
            'seller_product_bango': provider_product['resource_uri'],
            'redirect_url_onsuccess': redirect_url_onsuccess,
            'redirect_url_onerror': redirect_url_onerror,
            'icon_url': icon_url,
            'user_uuid': user_uuid,
            'application_size': application_size,
            'source': source
        })
        bill_id = res['billingConfigurationId']
        log.info('transaction {tr}: billing config ID: {bill}; '
                 'prices: {pr}'
                 .format(tr=transaction_uuid, bill=bill_id, pr=prices))

        return bill_id, self._formatted_payment_url(bill_id)


if not settings.SOLITUDE_URL:
    # This will typically happen when Sphinx builds the docs.
    warnings.warn('SOLITUDE_URL not found, not setting up client')
    client = None
else:
    log.info('Using universal SolitudeAPI')
    client = SolitudeAPI(settings.SOLITUDE_URL, settings.SOLITUDE_OAUTH)
