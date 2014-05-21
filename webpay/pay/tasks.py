import json
import logging
import sys
import urlparse
import uuid

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from celeryutils import task
import jwt
from lib.marketplace.api import client as mkt_client, UnknownPricePoint
from lib.solitude import constants
from lib.solitude.api import client, ProviderHelper
from multidb.pinning import use_master

from webpay.base.utils import gmtime, uri_to_pk
from webpay.constants import TYP_CHARGEBACK, TYP_POSTBACK
from .constants import NOT_SIMULATED, SIMULATED_POSTBACK, SIMULATED_CHARGEBACK
from .utils import send_pay_notice, trans_id

log = logging.getLogger('w.pay.tasks')
notify_kw = dict(default_retry_delay=15,  # seconds
                 max_tries=5)


class TransactionOutOfSync(Exception):
    """The transaction's state is unexpected."""


def configure_transaction(request, trans=None, mcc=None, mnc=None):
    """
    Begins a background task to configure a payment transaction.
    """
    if request.session.get('is_simulation', False):
        log.info('is_simulation: skipping configure payments step')
        return False

    notes = request.session.get('notes', {})
    if mcc and mnc:
        notes['network'] = {'mnc': mnc, 'mcc': mcc}
    else:
        # Reset network state to avoid leakage from previous states.
        notes['network'] = {}
    request.session['notes'] = notes
    log.info('Added mcc/mnc to session: '
             '{network}'.format(network=notes['network']))

    log.info('configuring transaction {0} from client'
             .format(request.session.get('trans_id')))

    if not trans and not 'trans_id' in request.session:
        log.error('trans_id: not found in session')
        return False

    try:
        if not trans:
            trans = client.get_transaction(uuid=request.session['trans_id'])
        log.info('attempt to reconfigure trans {0} (status={1})'
                 .format(request.session['trans_id'], trans['status']))
    except ObjectDoesNotExist:
        trans = {}

    if trans.get('status') in constants.STATUS_RETRY_OK:
        new_trans_id = trans_id()
        log.info('retrying trans {0} (status={1}) as {2}'
                 .format(request.session['trans_id'],
                         trans['status'], new_trans_id))
        request.session['trans_id'] = new_trans_id

    last_configured = request.session.get('configured_trans')
    if last_configured == request.session['trans_id']:
        log.info('trans %s (status=%r) already configured: '
                 'skipping configure payments step'
                 % (request.session['trans_id'], trans.get('status')))
        return False

    # Prevent configuration from running twice.
    request.session['configured_trans'] = request.session['trans_id']

    # Localize the product before sending it off to solitude/bango.
    _localize_pay_request(request)

    log.info('configuring payment in background for trans {t} (status={s}); '
             'Last configured: {c}'.format(t=request.session['trans_id'],
                                           s=trans.get('status'),
                                           c=last_configured))

    network = request.session['notes'].get('network', {})
    providers = ProviderHelper.supported_providers(
        mcc=network.get('mcc'),
        mnc=network.get('mnc'),
    )

    start_pay.delay(request.session['trans_id'],
                    request.session['notes'],
                    request.session['uuid'],
                    [p.name for p in providers])

    # We passed notes to start_pay (which saves it to the transaction
    # object), so delete it from the session to save cookie space.
    del request.session['notes']
    return True


def _localize_pay_request(request):
    if hasattr(request, 'locale'):
        try:
            pay_req = request.session['notes']['pay_request']
            req = pay_req['request']
        except KeyError:
            return

        trans_id = request.session.get('trans_id')

        locales = req.get('locales')
        if locales:
            fallback = request.locale.split('-')[0]
            if request.locale in locales:
                loc = locales[request.locale]
            elif fallback in locales:
                log.info('Fell back from {0} to {1} (iss: {2}, trans_id: {3})'
                         .format(request.locale, fallback, pay_req.get('iss'),
                                 trans_id))
                loc = locales[fallback]
            else:
                log.info(('No localization found for {0} (iss: {1}, '
                          'trans_id: {2})').format(request.locale,
                                                   pay_req.get('iss'),
                                                   trans_id))
                return

            req['name'] = loc.get('name', req['name'])
            req['description'] = loc.get('description', req['description'])


def get_secret(issuer_key):
    """Resolve the secret for this JWT."""
    if is_marketplace(issuer_key):
        return settings.SECRET
    else:
        return (client.slumber.generic.product
                      .get_object_or_404(public_id=issuer_key))['secret']


def get_provider_seller_uuid(issuer_key, product_data, provider_names):
    """Resolve the JWT into a seller uuid."""
    if is_marketplace(issuer_key):
        # The issuer of the JWT is Firefox Marketplace.
        # This is a special case where we need to find the
        # actual Solitude/Bango seller_uuid to associate the
        # product to the right account.
        try:
            public_id = product_data['public_id'][0]
        except KeyError:
            raise ValueError(
                'Marketplace {key} did not put a '
                'public_id in productData: {product_data}'.format(
                    key=settings.KEY, product_data=product_data
                )
            )
        log.info('Got public_id from Marketplace app purchase')
    else:
        # The issuer of the JWT is the seller.
        # Resolve this into the seller uuid.
        public_id = issuer_key
        log.info('Got public_id from in-app purchase')

    product = client.slumber.generic.product.get_object_or_404(
        public_id=public_id)
    seller = (client.slumber.generic.seller(uri_to_pk(product['seller']))
              .get_object_or_404())
    generic_seller_uuid = seller['uuid']

    for provider in provider_names:
        if product['seller_uuids'].get(provider, None) is not None:
            provider_seller_uuid = product['seller_uuids'][provider]
            log.info('Using provider seller uuid {s} for provider '
                     '{p} and for public_id {i}, generic seller uuid {u}'
                     .format(s=provider_seller_uuid, u=generic_seller_uuid,
                             p=provider, i=public_id))
            return (ProviderHelper(provider), provider_seller_uuid,
                    generic_seller_uuid)

    raise ValueError(
        'Unable to find a valid seller_uuid for public_id {public_id}'.format(
            public_id=public_id))


def is_marketplace(issuer_key):
    return issuer_key == settings.KEY


@task
@use_master
@transaction.commit_on_success
def start_pay(transaction_uuid, notes, user_uuid, provider_names, **kw):
    """
    Work with Solitude to begin a payment.

    This puts the transaction in a state where it's
    ready to be fulfilled by the payment provider.

    Arguments:

    **transaction_uuid**
        Unique identifier for a new transaction.

    **notes**
        Dict of notes about this transaction.

    **user_uuid**
        Unique identifier for the buyer user.

    **provider_names**
        A list of predefined provider names that this transaction can
        support. This list is influenced by region/carrier.
        Example: ['bango', 'boku'].

    """
    key = notes['issuer_key']
    pay = notes['pay_request']
    network = notes.get('network', {})
    product_data = urlparse.parse_qs(pay['request'].get('productData', ''))
    try:
        (provider_helper,
         provider_seller_uuid,
         generic_seller_uuid) = get_provider_seller_uuid(key,
                                                         product_data,
                                                         provider_names)
        try:
            application_size = int(product_data['application_size'][0])
        except (KeyError, ValueError):
            application_size = None

        # Ask the marketplace for a valid price point.
        # Note: the get_price_country API might be more helpful.
        prices = mkt_client.get_price(pay['request']['pricePoint'],
                                      provider=provider_helper.provider.name)
        log.debug('pricePoint=%s prices=%s' % (pay['request']['pricePoint'],
                                               prices['prices']))
        try:
            icon_url = (get_icon_url(pay['request'])
                        if settings.USE_PRODUCT_ICONS else None)
        except:
            log.exception('Calling get_icon_url')
            icon_url = None
        log.info('icon URL for %s: %s' % (transaction_uuid, icon_url))

        bill_id, pay_url, seller_id = provider_helper.start_transaction(
            transaction_uuid=transaction_uuid,
            generic_seller_uuid=generic_seller_uuid,
            provider_seller_uuid=provider_seller_uuid,
            product_id=pay['request']['id'],
            product_name=pay['request']['name'],
            prices=prices['prices'],
            icon_url=icon_url,
            user_uuid=user_uuid,
            application_size=application_size,
            source='marketplace' if is_marketplace(key) else 'other',
            mcc=network.get('mcc'),
            mnc=network.get('mnc')
        )
        trans_pk = client.slumber.generic.transaction.get_object(
            uuid=transaction_uuid)['resource_pk']
        client.slumber.generic.transaction(trans_pk).patch({
            'notes': json.dumps(notes),
            'uid_pay': bill_id,
            'pay_url': pay_url,
            'status': constants.STATUS_PENDING
        })
    except Exception, exc:
        log.exception('while configuring for payment')
        etype, val, tb = sys.exc_info()
        raise exc, None, tb


@task(**notify_kw)
@use_master
def payment_notify(transaction_uuid, **kw):
    """
    Notify the app of a successful payment by posting a JWT.

    The JWT sent is a mirror of the JWT used by the app to request payment
    except that it includes the following:

    :param response.transactionID: which is the Solitude transaction UUID.
    :param response.price: object that contains the amount and currency the
      customer actually paid in.
    """
    transaction = client.get_transaction(transaction_uuid)
    _notify(payment_notify, transaction)


@task(**notify_kw)
@use_master
def chargeback_notify(transaction_uuid, **kw):
    """
    Notify the app of a chargeback by posting a JWT.

    The JWT sent is the same as for payment notifications with the
    addition of response.reason, explained below.

    trans_id: pk of Transaction
    reason: either 'reversal' or 'refund'
    """
    transaction = client.get_transaction(transaction_uuid)
    _notify(chargeback_notify, transaction,
            extra_response={'reason': kw.get('reason', '')})


def _fake_amount(price_point):
    """
    For fake and simulated transactions we don't know the amount a customer
    paid. So we'll just pick the first random price from the tiers to make it
    realistic.
    """
    try:
        price = mkt_client.get_price(price_point)['prices'][0]
    except IndexError:
        # No prices were returned.
        raise IndexError('No prices for pricePoint: {0}'.format(price_point))
    except UnknownPricePoint:
        # This price point wasn't even valid.
        raise UnknownPricePoint('No pricePoint: {0}'.format(price_point))

    return {'amount': price['price'], 'currency': price['currency']}


@task(**notify_kw)
@use_master
def simulate_notify(issuer_key, pay_request, trans_uuid=None, **kw):
    """
    Post JWT notice to an app about a simulated payment.

    This isn't really much different from a regular notice except
    that a fake transaction_uuid is created.
    """
    if not trans_uuid:
        trans_uuid = 'simulate:%s' % uuid.uuid4()
    trans = {'uuid': trans_uuid,
             'notes': {'pay_request': pay_request,
                       'issuer_key': issuer_key}}

    trans.update(_fake_amount(pay_request['request']['pricePoint']))

    extra_response = None
    sim = pay_request['request']['simulate']
    if sim.get('reason'):
        extra_response = {'reason': sim['reason']}

    if sim['result'] == 'postback':
        trans['type'] = constants.TYPE_PAYMENT
        sim_flag = SIMULATED_POSTBACK
    elif sim['result'] == 'chargeback':
        trans['type'] = constants.TYPE_REFUND
        sim_flag = SIMULATED_CHARGEBACK
    else:
        raise NotImplementedError('Not sure how to simulate %s' % sim)

    log.info('Sending simulate notice %s to %s' % (sim, issuer_key))
    _notify(simulate_notify, trans, extra_response=extra_response,
            simulated=sim_flag, task_args=[issuer_key, pay_request])


def get_icon_url(request):
    """
    Given a payment request dict, this finds the best icon URL to cache.

    A cached URL will be returned on succes or None if it doesn't exist yet.
    """
    icons = request.get('icons')
    if not icons:
        return None
    sizes = icons.keys()
    size = settings.PRODUCT_ICON_SIZE
    if str(size) in sizes:
        # We have an exact match.
        ext_size = size
    else:
        # Get the biggest icon available.
        ext_size = max(sizes)
        if int(ext_size) < size:
            # We won't resize it so let's keep track of the size.
            size = ext_size

    url = icons[str(ext_size)]
    data = {
        'ext_url': url,
        'ext_size': ext_size,
        'size': size
    }
    try:
        res = mkt_client.api.webpay.product.icon.get_object(**data)
        return res['url']
    except ObjectDoesNotExist:
        # Queue the image to be fetched, resized and cached.
        mkt_client.api.webpay.product.icon.post(data)
        # The URL will be fetched on next purchase.
        return None


def _notify(notifier_task, trans, extra_response=None, simulated=NOT_SIMULATED,
            task_args=None):
    """
    Post JWT notice to an app server about a payment.
    """
    # TODO(Kumar) yell if transaction is not completed?
    typ, url = _prepare_notice(trans)
    response = {'transactionID': trans['uuid']}
    notes = trans['notes']
    if not task_args:
        task_args = [trans['uuid']]

    if extra_response:
        response.update(extra_response)

    response['price'] = {'amount': trans['amount'],
                         'currency': trans['currency']}
    issued_at = gmtime()
    notice = {'iss': settings.NOTIFY_ISSUER,
              'aud': notes['issuer_key'],
              'typ': typ,
              'iat': issued_at,
              'exp': issued_at + 3600,  # Expires in 1 hour
              'request': notes['pay_request']['request'],
              'response': response}
    log.info('preparing notice %s' % notice)

    signed_notice = jwt.encode(notice, get_secret(notes['issuer_key']),
                               algorithm='HS256')
    success, last_error = send_pay_notice(url, trans['type'], signed_notice,
                                          trans['uuid'], notifier_task,
                                          task_args, simulated=simulated)


def _prepare_notice(trans):
    request = trans['notes']['pay_request']['request']
    if trans['type'] == constants.TYPE_PAYMENT:
        return TYP_POSTBACK, request['postbackURL']
    elif trans['type'] == constants.TYPE_REFUND:
        return TYP_CHARGEBACK, request['chargebackURL']
    else:
        raise NotImplementedError('Unknown type: %s' % trans['type'])
