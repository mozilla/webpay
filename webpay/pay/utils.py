from datetime import datetime, timedelta
from urllib2 import HTTPError
from urlparse import urlparse
import logging

from django.conf import settings

from celery.exceptions import RetryTaskError
from django_statsd.clients import statsd
import requests
from requests.exceptions import RequestException

from lib.marketplace.api import client

from .models import NOT_SIMULATED

log = logging.getLogger('w.pay.utils')


def format_exception(exception):
    return u'%s: %s' % (exception.__class__.__name__, exception)


def send_pay_notice(url, notice_type, signed_notice, trans_id,
                    notifier_task, task_args, simulated=NOT_SIMULATED):
    """
    Send app a notification about a payment or chargeback.

    Parameters:

    **url**
        Absolute URL to notify.
    **notice_type**
        constant to indicate the type of notification being sent
    **signed_notice**
        encoded JWT with request and response
    **trans_id**
        Transaction ID of the notice. The recipient must respond
        with this ID.
    **notifier_task**
        celery task object
    **task_args**
        A list of args to send to the task when retrying after failures.
    **simulated**
        Type of payment simulation. The default is none.

    A tuple of (url, success, last_error) is returned.

    **url**
        Absolute URL where notification was sent
    **success**
        True if notification was successful
    **last_error**
        String to indicate the last exception message in the case of failure.
    """
    log.info('about to notify %s of notice type %s' % (url, notice_type))
    exception = None
    success = False

    try:
        with statsd.timer('purchase.send_pay_notice'):
            res = requests.post(url, {'notice': signed_notice}, timeout=5)
        res.raise_for_status()  # raise exception for non-200s
        res_content = res.text
    except (HTTPError, RequestException), exception:
        log.error('Notice for transaction %s raised exception in URL %s'
                  % (trans_id, url), exc_info=True)
        try:
            notifier_task.retry(args=task_args,
                eta=(datetime.now() +
                     timedelta(seconds=settings.POSTBACK_DELAY)),
                max_retries=settings.POSTBACK_ATTEMPTS,
                exc=exception)

        # Retry actually raises an exception, so let that through.
        except RetryTaskError:
            statsd.incr('purchase.send_pay_notice.retry')
            raise

        # If it's the last retry it will re-throw the original exception.
        except Exception, final_exception:
            if simulated == NOT_SIMULATED:
                notify_failure(url, trans_id)
            else:
                # TODO(Kumar): Fix the API for this in bug 847537
                log.info('Not notifying anyone about simulated failure '
                         'for %r' % trans_id)
            return False, format_exception(final_exception)

    else:
        if res_content == str(trans_id):
            success = True
            log.debug('URL %s responded OK for transaction %s '
                      'notification' % (url, trans_id))
        else:
            log.error('URL %s did not respond with transaction %s '
                      'for notification' % (url, trans_id))

    if exception:
        last_error = format_exception(exception)
    else:
        last_error = ''

    return success, last_error


def notify_failure(url, trans_id):
    statsd.incr('purchase.send_pay_notice.failure')
    client.slumber.api.webpay.failure(trans_id).patch({
                'attempts': settings.POSTBACK_ATTEMPTS,
                'url': url})
    log.exception('Retries failed to %s: %s:' % (url, trans_id))


def verify_urls(*urls, **kw):
    is_simulation = kw.pop('is_simulation', False)
    for url in urls:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError('Invalid URL: %s' % url)
        # If this is not a simulation, enforce URL schemes.
        if (not is_simulation and
            parsed.scheme not in settings.ALLOWED_CALLBACK_SCHEMES):
            raise ValueError('Schema must be one of: %s not %s' %
                             (settings.ALLOWED_CALLBACK_SCHEMES, url))
