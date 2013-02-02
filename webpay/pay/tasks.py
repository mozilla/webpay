import calendar
import json
import logging
import sys
import time
import urlparse
import uuid

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import transaction

from celeryutils import task
import jwt
from lib.marketplace.api import client as mkt_client
from lib.solitude import constants
from lib.solitude.api import client
from multidb.pinning import use_master

from webpay.base.helpers import absolutify
from webpay.constants import TYP_CHARGEBACK, TYP_POSTBACK
from .models import (Notice, NOT_SIMULATED, SIMULATED_POSTBACK,
                     SIMULATED_CHARGEBACK)
from .utils import send_pay_notice

log = logging.getLogger('w.pay.tasks')
notify_kw = dict(default_retry_delay=15,  # seconds
                 max_tries=5)


class TransactionOutOfSync(Exception):
    """The transaction's state is unexpected."""


def get_secret(issuer_key):
    """Resolve the secret for this JWT."""
    if is_marketplace(issuer_key):
        return settings.SECRET
    else:
        return (client.slumber.generic.product
                      .get_object_or_404(public_id=issuer_key))['secret']


def get_seller_uuid(issuer_key, product_data):
    """Resolve the JWT into a seller uuid."""
    if is_marketplace(issuer_key):
        # The issuer of the JWT is Firefox Marketplace.
        # This is a special case where we need to find the
        # actual Solitude/Bango seller_uuid to associate the
        # product to the right account.
        try:
            seller_uuid = urlparse.parse_qs(product_data)['seller_uuid'][0]
        except KeyError:
            raise ValueError('Marketplace %r did not put a seller_uuid '
                             'in productData: %r'
                             % (settings.KEY, product_data))
        log.info('Using real seller_uuid %r for Marketplace %r '
                 'app payment' % (seller_uuid, settings.KEY))
        return seller_uuid

    else:
        # The issuer of the JWT is the seller.
        # Resolve this into the seller uuid.
        #
        # TODO: we can speed this up by having product return the full data.
        product = (client.slumber.generic.product
                         .get_object_or_404(public_id=issuer_key))
        return (client.slumber.generic.seller(product['seller'].split('/')[-2])
                      .get_object_or_404())['uuid']


def is_marketplace(issuer_key):
    return issuer_key == settings.KEY


@task
@use_master
@transaction.commit_on_success
def start_pay(transaction_uuid, notes, **kw):
    """
    Work with Solitude to begin a Bango payment.

    This puts the transaction in a state where it's
    ready to be fulfilled by Bango.
    """
    # Because this is called from views, we get a new transaction every
    # time. If you re-use this task, you'd want to add some checking about the
    # transaction state.
    pay = notes['pay_request']
    try:
        seller_uuid = get_seller_uuid(notes['issuer_key'],
                                      pay['request'].get('productData', ''))
        # Ask the marketplace for a valid price point.
        prices = mkt_client.get_price(pay['request']['pricePoint'])
        # Set up the product for sale.
        bill_id, seller_product = client.configure_product_for_billing(
            transaction_uuid,
            seller_uuid,
            pay['request']['id'],
            pay['request']['name'],  # app/product name
            absolutify(reverse('bango.success')),
            absolutify(reverse('bango.error')),
            prices['prices']
        )
        trans_pk = client.slumber.generic.transaction.get_object(
            uuid=transaction_uuid)['resource_pk']
        client.slumber.generic.transaction(trans_pk).patch({
            'notes': json.dumps(notes),
            'uid_pay': bill_id,
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

    - A response.transactionID which is the Marketplace transaction ID
    - The price array only includes one entry, the actual price / currency
      that the customer paid in. The original request would include all
      possible prices / currencies.

    trans_id: pk of Transaction
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
            simulated=sim_flag)


def _notify(notifier_task, trans, extra_response=None, simulated=NOT_SIMULATED):
    """
    Post JWT notice to an app server about a payment.
    """
    # TODO(Kumar) yell if transaction is not completed?
    typ, url = _prepare_notice(trans)
    response = {'transactionID': trans['uuid']}
    notes = trans['notes']

    if extra_response:
        response.update(extra_response)

    issued_at = calendar.timegm(time.gmtime())
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
                                          trans['uuid'], notifier_task)
    s = Notice._meta.get_field_by_name('last_error')[0].max_length
    last_error = last_error[:s]  # truncate to fit
    Notice.objects.create(transaction_uuid=trans['uuid'],
                          success=success,
                          url=url,
                          simulated=simulated,
                          last_error=last_error)


def _prepare_notice(trans):
    request = trans['notes']['pay_request']['request']
    if trans['type'] == constants.TYPE_PAYMENT:
        return TYP_POSTBACK, request['postbackURL']
    elif trans['type'] == constants.TYPE_REFUND:
        return TYP_CHARGEBACK, request['chargebackURL']
    else:
        raise NotImplementedError('Unknown type: %s' % trans['type'])
