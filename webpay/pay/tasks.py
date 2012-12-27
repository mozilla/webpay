import calendar
import json
import logging
import sys
import time
import urlparse

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
from .models import Issuer, Notice
from .utils import send_pay_notice

log = logging.getLogger('w.pay.tasks')
notify_kw = dict(default_retry_delay=15,  # seconds
                 max_tries=5)


class TransactionOutOfSync(Exception):
    """The transaction's state is unexpected."""


def get_effective_issuer_key(issuer, issuer_key):
    if issuer and issuer.issuer_key:
        return issuer.issuer_key
    return issuer_key


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
    pay_request = notes['pay_request']
    iss = Issuer.objects.get(pk=notes['issuer']) if notes['issuer'] else None
    try:
        seller_uuid = get_effective_issuer_key(iss, notes['issuer_key'])
        if seller_uuid == settings.KEY:
            # The issuer of the JWT is Firefox Marketplace.
            # This is a special case where we need to find the
            # actual Solitude/Bango seller_uuid to associate the
            # product to the right account.
            prod_data = pay_request['request'].get('productData', '')
            try:
                seller_uuid = urlparse.parse_qs(prod_data)['seller_uuid'][0]
            except KeyError:
                raise ValueError('Marketplace %r did not put a seller_uuid '
                                 'in productData: %r' % (settings.KEY,
                                                         prod_data))
            log.info('Using real seller_uuid %r for Marketplace %r '
                     'app payment' % (seller_uuid, settings.KEY))

        # Ask the marketplace for a valid price point.
        prices = mkt_client.get_price(pay_request['request']['pricePoint'])
        # Set up the product for sale.
        bill_id, seller_product = client.configure_product_for_billing(
            transaction_uuid,
            seller_uuid,
            pay_request['request']['id'],
            pay_request['request']['name'],  # app/product name
            absolutify(reverse('bango.success')),
            absolutify(reverse('bango.error')),
            prices['prices']
        )
        # Now create a transaction.
        client.slumber.transaction.post({
            'notes': json.dumps(notes),
            'seller_product': seller_product,
            'uid_pay': bill_id,
            'uuid': transaction_uuid,
            'state': constants.STATUS_PENDING
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
def chargeback_notify(transaction_uuid, reason, **kw):
    """
    Notify the app of a chargeback by posting a JWT.

    The JWT sent is the same as for payment notifications with the
    addition of response.reason, explained below.

    trans_id: pk of Transaction
    reason: either 'reversal' or 'refund'
    """
    transaction = client.get_transaction(transaction_uuid)
    _notify(chargeback_notify, transaction, extra_response={'reason': reason})


def _notify(notifier_task, trans, extra_response=None):
    """
    Post JWT notice to an app server about a payment.
    """
    # TODO(Kumar) yell if transaction is not completed?
    #
    # Hmm not sure what to do here.
    if trans['notes']['issuer']:
        (private_key, url) = _prepare_inapp_notice(trans,
                                                   trans['notes']['issuer'])
    else:
        (private_key, url) = _prepare_mkt_notice(trans,
                                                 trans['notes']['issuer'],
                                                 trans['notes']['pay_request'])

    if trans['type'] == constants.TYPE_PAYMENT:
        typ = 'mozilla/payments/pay/postback/v1'
    elif trans['type'] == constants.TYPE_REFUND:
        typ = 'mozilla/payments/pay/chargeback/v1'
    else:
        raise NotImplementedError('Unknown type: %s' % trans['type'])

    response = {'transactionID': trans['uuid']}
    if extra_response:
        response.update(extra_response)

    issued_at = calendar.timegm(time.gmtime())
    notice = {'iss': settings.NOTIFY_ISSUER,
              'aud': trans['notes']['issuer_key'], # ...
              'typ': typ,
              'iat': issued_at,
              'exp': issued_at + 3600,  # Expires in 1 hour
              'request': trans['notes']['pay_request']['request'],
              'response': response}
    log.info('preparing notice %s' % notice)
    signed_notice = jwt.encode(notice,
                               private_key,
                               algorithm='HS256')
    success, last_error = send_pay_notice(url, trans['type'], signed_notice,
                                          trans['uuid'], notifier_task)

    s = Notice._meta.get_field_by_name('last_error')[0].max_length
    last_error = last_error[:s]  # truncate to fit
    Notice.objects.create(transaction_uuid=trans['uuid'],
                          success=success,
                          url=url,
                          last_error=last_error)


def _prepare_inapp_notice(trans, issuer):
    if trans['type'] == constants.TYPE_PAYMENT:
        uri = issuer.postback_url
    elif trans['type'] == constants.TYPE_REFUND:
        uri = issuer.chargeback_url
    else:
        raise NotImplementedError('Unknown type: %s' % trans['type'])
    url = urlparse.urlunparse((issuer.app_protocol(),
                               issuer.domain, uri, '',
                               '', ''))
    return (issuer.get_private_key(), url)


def _prepare_mkt_notice(trans, issuer, pay_request):
    if trans['notes']['issuer_key'] != settings.KEY:
        raise ValueError('key %r is not allowed to make app purchases'
                         % trans['notes']['issuer_key'])
    if trans['type'] == constants.TYPE_PAYMENT:
        if 'postbackURL' in pay_request['request']:
            url = pay_request['request']['postbackURL']
        else:
            url = settings.MKT_POSTBACK
    elif trans['type'] == constants.TYPE_REFUND:
        if 'chargebackURL' in pay_request['request']:
            url = pay_request['request']['chargebackURL']
        else:
            url = settings.MKT_CHARGEBACK
    else:
        raise NotImplementedError('Unknown type: %s' % trans['type'])
    return settings.SECRET, url
