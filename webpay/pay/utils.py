from django.conf import settings

from urllib2 import HTTPError
from urlparse import urlparse
import logging

import requests
from requests.exceptions import RequestException

log = logging.getLogger('w.pay.utils')


def send_pay_notice(url, notice_type, signed_notice, trans_id,
                    notifier_task):
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
        res = requests.post(url, signed_notice, timeout=5)
        res.raise_for_status()  # raise exception for non-200s
        res_content = res.text
    except (HTTPError, RequestException), exception:
        log.error('Notice for transaction %s raised exception in URL %s'
                  % (trans_id, url), exc_info=True)
        try:
            notifier_task.retry(exc=exception)
        except:
            log.exception('while retrying trans %s notice; '
                          'notification URL: %s' % (trans_id, url))
    else:
        if res_content == str(trans_id):
            success = True
            log.debug('URL %s responded OK for transaction %s '
                      'notification' % (url, trans_id))
        else:
            log.error('URL %s did not respond with transaction %s '
                      'for notification' % (url, trans_id))
    if exception:
        last_error = u'%s: %s' % (exception.__class__.__name__, exception)
    else:
        last_error = ''

    return success, last_error


def verify_urls(*urls):
    for url in urls:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError('Invalid URL: %s' % url)
        if parsed.scheme not in settings.ALLOWED_CALLBACK_SCHEMES:
            raise ValueError('Schema must be one of: %s not %s' %
                             (settings.ALLOWED_CALLBACK_SCHEMES, url))
