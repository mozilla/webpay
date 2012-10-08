import calendar
import logging
import time

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
def payment_notify(payment_id, **kw):
    """
    Notify the app of a successful payment by posting a JWT.

    The JWT sent is a mirror of the JWT used by the app to request payment
    except that it includes the following:

    - A response.transactionID which is the Marketplace transaction ID
    - The price array only includes one entry, the actual price / currency
      that the customer paid in. The original request would include all
      possible prices / currencies.

    payment_id: pk of InappPayment
    """
    log.debug('sending payment notice for payment %s' % payment_id)
    _notify(payment_id, payments.INAPP_NOTICE_PAY, payment_notify)


@task(**notify_kw)
@use_master
def chargeback_notify(payment_id, reason, **kw):
    """
    Notify the app of a chargeback by posting a JWT.

    The JWT sent is the same as for payment notifications with the
    addition of response.reason, explained below.

    payment_id: pk of InappPayment
    reason: either 'reversal' or 'refund'
    """
    log.debug('sending chargeback notice for payment %s, reason %r'
              % (payment_id, reason))
    _notify(payment_id, payments.INAPP_NOTICE_CHARGEBACK,
            chargeback_notify,
            extra_response={'reason': reason})


def _notify(payment_id, notice_type, notifier_task, extra_response=None):
    """
    Post JWT notice to an app server about a payment.

    This is only for in-app payments. For Marketple app purchases
    notices can be sent more efficiently through another celery task.
    """
    payment = InappPayment.objects.get(pk=payment_id)
    config = payment.config
    contrib = payment.contribution
    if notice_type == payments.INAPP_NOTICE_PAY:
        typ = 'mozilla/payments/pay/postback/v1'
    elif notice_type == payments.INAPP_NOTICE_CHARGEBACK:
        typ = 'mozilla/payments/pay/chargeback/v1'
    else:
        raise NotImplementedError('Unknown type: %s' % notice_type)
    response = {'transactionID': contrib.pk}
    if extra_response:
        response.update(extra_response)
    issued_at = calendar.timegm(time.gmtime())
    signed_notice = jwt.encode({'iss': settings.NOTIFY_ISSUER,
                                'aud': config.public_key,
                                'typ': typ,
                                'iat': issued_at,
                                'exp': issued_at + 3600,  # Expires in 1 hour
                                'request': {
                                    'price': [{
                                        'amount': str(contrib.amount),
                                        'currency': contrib.currency
                                     }],
                                     'name': payment.name,
                                     'description': payment.description,
                                     'productdata': payment.app_data
                                },
                                'response': response},
                               config.get_private_key(),
                               algorithm='HS256')
    url, success, last_error = send_pay_notice(notice_type, signed_notice,
                                               config, contrib, notifier_task)

    s = InappPayNotice._meta.get_field_by_name('last_error')[0].max_length
    last_error = last_error[:s]  # truncate to fit
    InappPayNotice.objects.create(payment=payment,
                                  notice=notice_type,
                                  success=success,
                                  url=url,
                                  last_error=last_error)
