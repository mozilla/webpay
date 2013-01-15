from django import http
from django.shortcuts import render
from django.views.decorators.http import require_GET

import commonware.log
from slumber.exceptions import HttpClientError

from lib.solitude.api import client
from webpay.pay import tasks

log = commonware.log.getLogger('w.bango')


def _record(request):
    """
    Records the request into solitude. If something went wrong it will
    return False.
    """
    if 'trans_id' not in request.session:
        log.info('Bango success called without an active '
                 'transaction in the session')
        return False

    qs = request.GET
    trans_uuid = qs.get('MerchantTransactionId')
    if trans_uuid != request.session['trans_id']:
        log.info('Bango query string transaction %r is not in the '
                 'active session' % trans_uuid)
        return False

    try:
        client.slumber.bango.notification.post({
            'moz_signature': qs.get('MozSignature'),
            'moz_transaction': trans_uuid,
            'billing_config_id': qs.get('BillingConfigurationId'),
            'bango_response_code': qs.get('ResponseCode'),
            'bango_response_message': qs.get('ResponseMessage'),
            'bango_trans_id': qs.get('BangoTransactionId'),
        })
    except HttpClientError, err:
        log.info('Bango payment notice for transaction uuid %r '
                 'failed: %s' % (trans_uuid, err))
        return False

    return True


@require_GET
def success(request):
    log.info('Bango success: %s' % request.GET)

    # We should only have OK's coming from Bango, presumably.
    if request.GET.get('ResponseCode') != 'OK':
        log.info('Invalid response code: %s' % request.GET.get('ResponseCode'))
        return http.HttpResponseBadRequest()

    if not _record(request):
        return http.HttpResponseBadRequest()

    # Signature verification was successful; fulfill the payment.
    tasks.payment_notify.delay(request.GET.get('MerchantTransactionId'))
    return render(request, 'bango/success.html')


@require_GET
def error(request):
    log.info('Bango error: %s' % request.GET)

    # We should NOT have OK's coming from Bango, presumably.
    if request.GET.get('ResponseCode') == 'OK':
        log.info('Invalid response code: %s' % request.GET.get('ResponseCode'))
        return http.HttpResponseBadRequest()

    if not _record(request):
        return http.HttpResponseBadRequest()

    return render(request, 'bango/error.html', {})
