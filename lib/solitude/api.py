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

from lib.marketplace.constants import COUNTRIES
from webpay.base import dev_messages as msg
from webpay.base.helpers import absolutify

from . import constants as solitude_const
from .errors import ERROR_STRINGS
from .exceptions import ResourceNotModified
from ..utils import SlumberWrapper


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

    def create_buyer(self, uuid, email, pin=None, pin_confirmed=False):
        """Creates a buyer with an optional PIN in solitude.

        :param uuid: String to identify the buyer by.
        :param pin: Optional PIN that will be hashed.
        :param pin_confirmed: Optional boolean to set if the PIN was already
                              confirmed in the UI.
        :rtype: dictionary
        """
        pin_data = {
            'uuid': uuid,
            'email': email,
            'pin': pin,
            'pin_confirmed': bool(pin_confirmed and pin),
        }

        obj = self.safe_run(self.slumber.generic.buyer.post, pin_data)

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

    def update_buyer(self, uuid, etag='', **kwargs):
        """Updates a buyer identified by their uuid.

        :param uuid: String to identify the buyer by.
        :rtype: dictionary
        """
        id_ = self.get_buyer(uuid).get('resource_pk')
        res = self.safe_run(self.slumber.generic.buyer(id=id_).patch,
                            kwargs,
                            headers={'If-Match': etag})
        if 'errors' in res:
            return res
        return {}

    def set_needs_pin_reset(self, uuid, value=True, etag=''):
        """Set flag for user to go through reset flow or not on next log in.

        :param uuid: String to identify the buyer by.
        :param value: Boolean for whether they should go into the reset flow or
                      not, defaults to True
        :rtype: dictionary
        """
        return self.update_buyer(uuid,
                                 etag=etag,
                                 needs_pin_reset=value,
                                 new_pin=None)

    def unset_was_locked(self, uuid, etag=''):
        """Unsets the flag to view the was_locked screen.

        :param uuid: String to identify the buyer by.
        :rtype: dictionary
        """
        return self.update_buyer(uuid, etag=etag, pin_was_locked_out=False)

    def change_pin(self, uuid, pin, etag='', pin_confirmed=False,
                   clear_was_locked=False):
        """Changes the pin of a buyer, for use with buyers who exist without
        pins.

        :param buyer_id integer: ID of the buyer you'd like to change the PIN
                                 for.
        :param pin: PIN the user would like to change to.
        :param pin_confirmed: Boolean to set if the PIN was already confirmed
                              in the UI.
        :param clear_was_locked: Boolean to clear the pin_was_locked_out state
                                 if the PIN was changed by the user.
        :rtype: dictionary
        """
        pin_data = {'pin': pin, 'pin_confirmed': pin_confirmed}
        if clear_was_locked:
            pin_data['pin_was_locked_out'] = False

        return self.update_buyer(uuid, etag=etag, **pin_data)

    def set_new_pin(self, uuid, new_pin, etag=''):
        """Sets the new_pin for use with a buyer that is resetting their pin.

        :param buyer_id integer: ID of the buyer you'd like to change the PIN
                                 for.
        :param pin: PIN the user would like to change to.
        :rtype: dictionary
        """
        return self.update_buyer(uuid, etag=etag, new_pin=new_pin)

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
    def supported_providers(cls, mcc=None, mnc=None):
        """
        Given the user's mobile network (when available) return a list of
        all suitable provider helper objects in order of preference.

        Keyword arguments:

        **mcc**
            The user's mobile carrier code, if known.

        **mnc**
            The user's mobile network code, if known.
        """
        if settings.PAYMENT_PROVIDER == BokuProvider.name:
            raise ValueError('Since Boku is detected by network '
                             'use SIMULATED_NETWORK to force it instead')

        supported_providers = []

        # Allow Boku when on one of their networks.
        if (mcc, mnc) in BokuProvider.network_data:
            supported_providers.append(BokuProvider.name)

        # Always allow the default provider.
        supported_providers.append(settings.PAYMENT_PROVIDER)

        return [cls(provider_name) for provider_name in supported_providers]

    def start_transaction(self, transaction_uuid,
                          generic_seller_uuid, provider_seller_uuid,
                          product_id, product_name,
                          prices, icon_url,
                          user_uuid, application_size,
                          source='unknown',
                          mcc=None, mnc=None):
        """
        Start a payment provider transaction to begin the purchase flow.
        """
        try:
            generic_seller = self.slumber.generic.seller.get_object_or_404(
                uuid=generic_seller_uuid)
        except ObjectDoesNotExist:
            raise SellerNotConfigured(
                '{pr}: Seller with uuid {u} does not exist'
                .format(u=generic_seller_uuid, pr=self.provider.name))
        generic_seller_id = generic_seller['resource_pk']
        log.info('{pr}: starting transaction {tr}: generic seller: {sel}'
                 .format(tr=transaction_uuid, sel=generic_seller_id,
                         pr=self.provider.name))
        log.info('{pr}: get product for seller_uuid={uuid} external_id={ext}'
                 .format(pr=self.provider.name,
                         uuid=generic_seller_uuid, ext=product_id))

        product = None
        try:
            product = self.slumber.generic.product.get_object_or_404(
                external_id=product_id,
                seller=generic_seller_id,
            )
            log.info('{pr}: found generic product {prod}'
                     .format(pr=self.provider.name, prod=product))
            provider_product = self.provider.get_product(generic_seller,
                                                         product)
            log.info('{pr}: found provider product {prod}'
                     .format(prod=provider_product, pr=self.provider.name))
        except ObjectDoesNotExist:
            product, provider_product = self.create_product(
                external_id=product_id, product_name=product_name,
                generic_seller=generic_seller, generic_product=product,
                provider_seller_uuid=provider_seller_uuid)


        trans_token, pay_url = self.provider.create_transaction(
            generic_seller=generic_seller,
            generic_product=product,
            provider_product=provider_product,
            provider_seller_uuid=provider_seller_uuid,
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

        return trans_token, pay_url, generic_seller_id

    def create_product(self, external_id, product_name, generic_seller,
                       provider_seller_uuid, generic_product=None):
        """
        Creates a generic product and provider product on the fly.

        This is for scenarios like adhoc in-app payments where the
        system might be selling a product for the first time.
        """
        log.info('{pr}: creating product with name: {name}, '
                 'external_id: {ext_id}, generic seller: {seller} '
                 'provider seller: {provider_seller_uuid}'
                 .format(name=product_name, ext_id=external_id,
                         seller=generic_seller, pr=self.provider.name,
                         provider_seller_uuid=provider_seller_uuid))

        # If there is no provider seller it means the billing account has
        # not yet been set up in Devhub. Thus, we're not catching an exception
        # here.
        provider_seller = self.provider.get_seller(
            generic_seller=generic_seller,
            provider_seller_uuid=provider_seller_uuid
        )

        # Now that we're sure the seller is set up, create a generic and
        # provider specific product.
        if not generic_product:
            generic_product = self.slumber.generic.product.post({
                'external_id': external_id,
                'seller': generic_seller['resource_uri'],
                'public_id': str(uuid.uuid4()),
                'access': solitude_const.ACCESS_PURCHASE,
            })
            log.info('{pr}: created generic product {prod}'
                     .format(prod=generic_product, pr=self.provider.name))

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

        Returns the Solitude transaction UUID.
        """
        # Get the notification data from the incoming request.
        data = self.provider.get_notification_data(request)

        log.info('Provider={pr} verifying notification: {data}'
                 .format(pr=self.name, data=data))
        try:
            # Post the result to solitude.
            transaction_uuid = self.provider.verify_notification(data)
        except HttpClientError, err:
            log.error('Provider={pr} post failed: {err}'
                      .format(pr=self.name, err=err))
            raise msg.DevMessage(msg.NOTICE_ERROR)

        return transaction_uuid


_registry = {}


def provider_cls(name):
    return _registry[name]


def register_provider(cls):
    _registry[cls.name] = cls
    return cls


class PayProvider(object):
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
        """
        Returns the provider specific product object from Solitude.
        """
        raise NotImplementedError()

    def create_product(self, generic_product, provider_seller, external_id,
                       product_name):
        return self.api.products.post({
            'external_id': external_id,
            'seller_id': provider_seller['resource_pk'],
            'name': product_name,
        })

    def get_seller(self, generic_seller, provider_seller_uuid):
        """
        Returns a provider-specific seller object from Solitude.
        """
        raise NotImplementedError()

    def create_transaction(self, generic_seller, generic_product,
                           provider_product, provider_seller_uuid,
                           product_name, transaction_uuid,
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
        """
        Get the Solitude transaction ID from the query string on a notification
        URL.
        """
        return parsed_qs.get('ext_transaction_id')

    def get_notice_result(self, parsed_qs, raw_qs):
        return self.api.notices.post({'qs': raw_qs})

    def get_notification_data(self, request):
        """
        Given a provider-specific GET/POST request, return a dict of
        notification data that can be used for verification.

        For example, a provider might notify Webpay of a successful
        transaction. That request might include a signature that can
        be used to verify authenticity.
        """
        raise NotImplementedError

    def verify_notification(self, data):
        """
        Verify provider notification using params from get_notification_data().

        This will raise an exception on any kind of verification error.
        This will also raise an exception if the transaction has already
        been processed.

        Returns the Solitude transaction UUID.
        """
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

    def get_product(self, generic_seller, generic_product):
        # This returns a partial result.
        listing = self.api.products.get_object_or_404(
            seller_product__seller=generic_seller['resource_pk'],
            seller_product__external_id=generic_product['external_id'])
        # This pings zippy and returns us a full result.
        return self.api.products(id=listing['id']).get_object_or_404()

    def create_transaction(self, generic_seller, generic_product,
                           provider_product, provider_seller_uuid,
                           product_name, transaction_uuid,
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
            'product_id': provider_product[self.name]['uuid'],
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
            'seller': generic_seller['resource_uri'],
            'seller_product': generic_product['resource_uri'],
            'source': source,
            'region': region,
            'carrier': carrier,
            'type': solitude_const.TYPE_PAYMENT,
            'amount': price,
            'currency': currency,
        })
        log.info('made solitude trans {trans}'.format(trans=trans))

        token = provider_trans['token']
        return token, self._formatted_payment_url(token)

    def get_seller(self, generic_seller, provider_seller_uuid):
        return (self.api.sellers(generic_seller['resource_pk'])
                .get_object_or_404())


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

    def __init__(self, *args, **kw):
        super(BokuProvider, self).__init__(*args, **kw)
        # Don't use this unless you have to. Hopefully we can delete it soon.
        self.provider_api = self.slumber.provider.boku

    @property
    def api(self):
        return self.slumber.boku

    def get_product(self, generic_seller, generic_product):
        # Boku does not have a products API the way Bango does.
        return None

    def create_product(self, generic_product, provider_seller, external_id,
                       product_name):
        # Boku does not have a products API the way Bango does.
        return None

    def create_transaction(self, generic_seller, generic_product,
                           provider_product, provider_seller_uuid,
                           product_name, transaction_uuid,
                           prices, user_uuid, application_size, source,
                           icon_url, mcc=None, mnc=None):
        try:
            # Do a sanity check to make sure we're actually on a Boku network.
            self.network_data[(mcc, mnc)]
        except KeyError:
            raise self.TransactionError('Unknown Boku network: '
                                        'mcc={mcc}; mnc={mnc}'
                                        .format(mcc=mcc, mnc=mnc))
        country = mobile_codes.mcc(mcc)
        # TODO: consider using get_price_country here?
        mcc_region = COUNTRIES[mcc]
        price = None
        for mktpl_price in prices:
            # Given a list of all prices + currencies for this price point,
            # send Boku the one that matches the user's network/region.
            if mktpl_price['region'] == mcc_region:
                price = mktpl_price['price']
                break
        if not price:
            log.error('No Boku price for region {r}: mcc={mcc}; mnc={mnc} '
                      'in prices {pr}'.format(mcc=mcc, mnc=mnc,
                                              r=mcc_region, pr=prices))
            raise self.TransactionError(
                'Could not find a price for region {r}: mcc={mcc}; mnc={mnc}'
                .format(mcc=mcc, mnc=mnc, r=mcc_region))

        provider_trans = self.api.transactions.post({
            'forward_url': absolutify(reverse('provider.wait_to_finish',
                                              args=[self.name])),
            'callback_url': absolutify(reverse('provider.notification',
                                               args=[self.name])),
            'country': country.alpha2,
            # TODO: figure out error callbacks in bug 987843.
            # 'error_url': absolutify(reverse('provider.error',
            #                                 args=[self.name])),
            'price': price,
            'seller_uuid': provider_seller_uuid,
            'transaction_uuid': transaction_uuid,
            'user_uuid': user_uuid,
        })
        log.info('{pr}: made provider trans {trans}'
                 .format(pr=self.name, trans=provider_trans))

        trans = self.slumber.generic.transaction.post({
            'provider': solitude_const.PROVIDERS[self.name],
            'seller': generic_seller['resource_uri'],
            'seller_product': generic_product['resource_uri'],
            'source': source,
            'status': solitude_const.STATUS_PENDING,
            'type': solitude_const.TYPE_PAYMENT,
            'uuid': transaction_uuid,
        })
        log.info('{pr}: made solitude trans {trans}'
                 .format(pr=self.name, trans=trans))

        return provider_trans['transaction_id'], provider_trans['buy_url']

    def get_notification_data(self, request):
        return request.GET

    def get_seller(self, generic_seller, provider_seller_uuid):
        # TODO: this is waiting on a Solitude API to get a provider specific
        # seller from a generic seller.
        # It is currently unused because Boku does not have products the
        # way Bango does.
        return None

    def verify_notification(self, data):
        # This will raise a client error on a non 2xx response.
        # This gets a 400 response if the transaction has already been
        # processed so that too will raise an exception.
        self.provider_api.event.post(data)
        return data['param']  # Solitude transaction UUID.

    def transaction_from_notice(self, parsed_qs):
        return parsed_qs.get('param')


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

    def get_seller(self, generic_seller, provider_seller_uuid):
        # The generic seller is linked to our generic product.
        # We want to get the provider specific seller so we can get the
        # Bango package.
        provider_generic_seller = (self.slumber.generic.seller
                                   .get_object(uuid=provider_seller_uuid))
        if not provider_generic_seller['bango']:
            raise ValueError(
                'No bango account set up for {sel}'
                .format(sel=provider_generic_seller['resource_pk']))
        return provider_generic_seller['bango']

    def create_transaction(self, generic_seller, generic_product,
                           provider_product, provider_seller_uuid,
                           product_name, transaction_uuid,
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

    def transaction_from_notice(self, parsed_qs):
        raise NotImplementedError()


if not settings.SOLITUDE_URL:
    # This will typically happen when Sphinx builds the docs.
    warnings.warn('SOLITUDE_URL not found, not setting up client')
    client = None
else:
    log.info('Using universal SolitudeAPI')
    client = SolitudeAPI(settings.SOLITUDE_URL, settings.SOLITUDE_OAUTH)
