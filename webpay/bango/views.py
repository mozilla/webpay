from django import http
from django.shortcuts import render
from django.views.decorators.http import require_GET

import commonware.log
from slumber.exceptions import HttpClientError

from lib.solitude.api import client
from webpay.pay import tasks

log = commonware.log.getLogger('w.bango')


@require_GET
def success(request):
    log.info('Bango success: %s' % request.GET)
    if 'trans_id' not in request.session:
        log.info('Bango success called without an active '
                 'transaction in the session')
        return http.HttpResponseBadRequest()
    qs = request.GET
    trans_uuid = qs.get('MerchantTransactionId')
    if trans_uuid != request.session['trans_id']:
        log.info('Bango query string transaction %r is not in the '
                 'active session' % trans_uuid)
        return http.HttpResponseBadRequest()
    try:
        client.slumber.bango.payment_notice.post({
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
        return http.HttpResponseBadRequest()

    # Signature verification was successful; fulfill the payment.
    tasks.payment_notify.delay(trans_uuid)
    return render(request, 'bango/success.html')


@require_GET
def error(request):
    # TODO(Kumar) process errors in bug 828513.
    log.info('Bango error: %s' % request.GET)
    return render(request, 'bango/error.html', {})
