import calendar
import logging
import time
import urlparse

from django.conf import settings

from celeryutils import task
from gelato.constants import payments
import jwt
from multidb.pinning import use_master

from .models import InappPayNotice, InappPayment
from .utils import send_pay_notice

log = logging.getLogger('w.pay.tasks')
notify_kw = dict(default_retry_delay=15,  # seconds
                 max_tries=5)


@task(**notify_kw)
@use_master
def payment_notify(payment_id=None, pay_request=None, public_key=None,
                   **kw):
    """
    Notify the app of a successful payment by posting a JWT.

    The JWT sent is a mirror of the JWT used by the app to request payment
    except that it includes the following:

    - A response.transactionID which is the Marketplace transaction ID
    - The price array only includes one entry, the actual price / currency
      that the customer paid in. The original request would include all
      possible prices / currencies.

    payment_id: pk of InappPayment
    pay_request: JSON request
    public_key: public_key for notification recipient if no payment_id
    """
    _notify(payments.INAPP_NOTICE_PAY, payment_notify,
            payment_id=payment_id, pay_request=pay_request,
            public_key=public_key)


@task(**notify_kw)
@use_master
def chargeback_notify(reason, payment_id=None, pay_request=None,
                      public_key=None, **kw):
    """
    Notify the app of a chargeback by posting a JWT.

    The JWT sent is the same as for payment notifications with the
    addition of response.reason, explained below.

    payment_id: pk of InappPayment
    pay_request: JSON request
    public_key: public_key for notification recipient if no payment_id
    reason: either 'reversal' or 'refund'
    """
    _notify(payments.INAPP_NOTICE_CHARGEBACK,
            chargeback_notify, public_key=public_key,
            payment_id=payment_id, pay_request=pay_request,
            extra_response={'reason': reason})


def _notify(notice_type, notifier_task, extra_response=None,
            payment_id=None, pay_request=None, public_key=None):
    """
    Post JWT notice to an app server about a payment.

    This is only for in-app payments. For Marketple app purchases
    notices can be sent more efficiently through another celery task.
    """
    if payment_id:
        (public_key, private_key, url,
         pay_request, trans_id) = _prepare_inapp_notice(notice_type,
                                                        payment_id)
    elif pay_request:
        (public_key, private_key, url,
         pay_request, trans_id) = _prepare_mkt_notice(notice_type,
                                                      public_key,
                                                      pay_request)
    else:
        raise ValueError('Both payment_id and pay_request were None')

    if notice_type == payments.INAPP_NOTICE_PAY:
        typ = 'mozilla/payments/pay/postback/v1'
    elif notice_type == payments.INAPP_NOTICE_CHARGEBACK:
        typ = 'mozilla/payments/pay/chargeback/v1'
    else:
        raise NotImplementedError('Unknown type: %s' % notice_type)

    response = {'transactionID': trans_id}
    if extra_response:
        response.update(extra_response)
    issued_at = calendar.timegm(time.gmtime())
    signed_notice = jwt.encode({'iss': settings.NOTIFY_ISSUER,
                                'aud': public_key,
                                'typ': typ,
                                'iat': issued_at,
                                'exp': issued_at + 3600,  # Expires in 1 hour
                                'request': pay_request,
                                'response': response},
                               private_key,
                               algorithm='HS256')
    success, last_error = send_pay_notice(url, notice_type, signed_notice,
                                          trans_id, notifier_task)

    s = InappPayNotice._meta.get_field_by_name('last_error')[0].max_length
    last_error = last_error[:s]  # truncate to fit
    # TODO(Kumar) fixme: save payment for app purchases.
    #InappPayNotice.objects.create(payment=payment,
    #                              notice=notice_type,
    #                              success=success,
    #                              url=url,
    #                              last_error=last_error)


def _prepare_inapp_notice(notice_type, payment_id):
    payment = InappPayment.objects.get(pk=payment_id)
    config = payment.config
    contrib = payment.contribution
    pay_request = {
        'price': [{
            'amount': str(contrib.amount),
            'currency': contrib.currency
         }],
         'name': payment.name,
         'description': payment.description,
         'productdata': payment.app_data
    }
    if notice_type == payments.INAPP_NOTICE_PAY:
        uri = config.postback_url
    elif notice_type == payments.INAPP_NOTICE_CHARGEBACK:
        uri = config.chargeback_url
    else:
        raise NotImplementedError('Unknown type: %s' % notice_type)
    url = urlparse.urlunparse((config.app_protocol(),
                               config.addon.parsed_app_domain.netloc, uri, '',
                               '', ''))
    return (config.public_key, config.get_private_key(),
            url, pay_request, contrib.pk)


def _prepare_mkt_notice(notice_type, key, pay_request):
    if key != settings.KEY:
        raise ValueError('key %r is not allowed to make app purchases'
                         % key)
    log.info('preparing mkt notice from %s' % pay_request)
    if notice_type == payments.INAPP_NOTICE_PAY:
        if 'postbackURL' in pay_request['request']:
            url = pay_request['request']['postbackURL']
        else:
            url = settings.MKT_POSTBACK
    elif notice_type == payments.INAPP_NOTICE_CHARGEBACK:
        if 'chargebackURL' in pay_request['request']:
            url = pay_request['request']['chargebackURL']
        else:
            url = settings.MKT_CHARGEBACK
    else:
        raise NotImplementedError('Unknown type: %s' % notice_type)
    # Simulate app purchase!
    # TODO(Kumar): fixme
    trans_id = -1
    return (settings.KEY, settings.SECRET, url, pay_request['request'],
            trans_id)
