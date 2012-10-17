import calendar
import json
import logging
import time
import urlparse

from django.conf import settings

from celeryutils import task
import jwt
from multidb.pinning import use_master

from .models import Notice, Transaction, TRANS_PAY, TRANS_REFUND
from .utils import send_pay_notice

log = logging.getLogger('w.pay.tasks')
notify_kw = dict(default_retry_delay=15,  # seconds
                 max_tries=5)


@task(**notify_kw)
@use_master
def payment_notify(trans_id, **kw):
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
    _notify(payment_notify, trans_id)


@task(**notify_kw)
@use_master
def chargeback_notify(trans_id, reason, **kw):
    """
    Notify the app of a chargeback by posting a JWT.

    The JWT sent is the same as for payment notifications with the
    addition of response.reason, explained below.

    trans_id: pk of Transaction
    reason: either 'reversal' or 'refund'
    """
    _notify(chargeback_notify,
            trans_id, extra_response={'reason': reason})


def _notify(notifier_task, trans_id,
            extra_response=None):
    """
    Post JWT notice to an app server about a payment.

    This is only for in-app payments. For Marketple app purchases
    notices can be sent more efficiently through another celery task.
    """
    trans = Transaction.objects.get(pk=trans_id)
    pay_request = json.loads(trans.json_request)
    # TODO(Kumar) yell if transaction is not completed?
    if trans.issuer:
        (private_key, url) = _prepare_inapp_notice(trans)
    else:
        (private_key, url) = _prepare_mkt_notice(trans,
                                                 pay_request)

    if trans.typ == TRANS_PAY:
        typ = 'mozilla/payments/pay/postback/v1'
    elif trans.typ == TRANS_REFUND:
        typ = 'mozilla/payments/pay/chargeback/v1'
    else:
        raise NotImplementedError('Unknown type: %s' % trans.typ)

    response = {'transactionID': trans.pk}
    if extra_response:
        response.update(extra_response)
    issued_at = calendar.timegm(time.gmtime())
    notice = {'iss': settings.NOTIFY_ISSUER,
              'aud': trans.issuer_key,
              'typ': typ,
              'iat': issued_at,
              'exp': issued_at + 3600,  # Expires in 1 hour
              'request': pay_request['request'],
              'response': response}
    log.info('preparing notice %s' % notice)
    signed_notice = jwt.encode(notice,
                               private_key,
                               algorithm='HS256')
    success, last_error = send_pay_notice(url, trans.typ, signed_notice,
                                          trans.pk, notifier_task)

    s = Notice._meta.get_field_by_name('last_error')[0].max_length
    last_error = last_error[:s]  # truncate to fit
    Notice.objects.create(transaction=trans,
                          success=success,
                          url=url,
                          last_error=last_error)


def _prepare_inapp_notice(trans):
    if trans.typ == TRANS_PAY:
        uri = trans.issuer.postback_url
    elif trans.typ == TRANS_REFUND:
        uri = trans.issuer.chargeback_url
    else:
        raise NotImplementedError('Unknown type: %s' % trans.typ)
    url = urlparse.urlunparse((trans.issuer.app_protocol(),
                               trans.issuer.domain, uri, '',
                               '', ''))
    return (trans.issuer.get_private_key(), url)


def _prepare_mkt_notice(trans, pay_request):
    if trans.issuer_key != settings.KEY:
        raise ValueError('key %r is not allowed to make app purchases'
                         % trans.issuer_key)
    if trans.typ == TRANS_PAY:
        if 'postbackURL' in pay_request['request']:
            url = pay_request['request']['postbackURL']
        else:
            url = settings.MKT_POSTBACK
    elif trans.typ == TRANS_REFUND:
        if 'chargebackURL' in pay_request['request']:
            url = pay_request['request']['chargebackURL']
        else:
            url = settings.MKT_CHARGEBACK
    else:
        raise NotImplementedError('Unknown type: %s' % trans.typ)
    return settings.SECRET, url
