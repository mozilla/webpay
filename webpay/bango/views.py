from django.shortcuts import render
from django.views.decorators.http import require_GET

import commonware.log
from slumber.exceptions import HttpClientError

from lib.solitude.api import client
from webpay.base.utils import _error
from webpay.pay import tasks

log = commonware.log.getLogger('w.bango')


def _record(request):
    """
    Records the request into solitude. If something went wrong it will
    return False.
    """
    qs = request.GET
    session_uuid = request.session.get('trans_id')
    trans_uuid = qs.get('MerchantTransactionId')

    if session_uuid and trans_uuid != session_uuid:
        log.info('Bango query string transaction %r is not in the '
                 'active session' % trans_uuid)
        return False
    elif not trans_uuid:
        log.info('No uuid in the session or query string: %s' %
                 request.session.session_key)
        return False

    try:
        client.slumber.bango.notification.post({
            'moz_signature': qs.get('MozSignature'),
            'moz_transaction': trans_uuid,
            'billing_config_id': qs.get('BillingConfigurationId'),
            'bango_response_code': qs.get('ResponseCode'),
            'bango_response_message': qs.get('ResponseMessage'),
            'bango_trans_id': qs.get('BangoTransactionId'),
            'amount': qs.get('Price'),
            'currency': qs.get('Currency'),
        })
    except HttpClientError, err:
        log.info('Bango payment notice for transaction uuid %r '
                 'failed: %s' % (trans_uuid, err))
        return False

    return True


@require_GET
def success(request):
    """
    Process a redirect request after the Bango payment has completed.
    This URL endpoint is pre-arranged with Bango via the Billing Config API.

    Example request:

    ?ResponseCode=OK&ResponseMessage=Success&BangoUserId=1473894939
    &MerchantTransactionId=webpay%3a14d6a53c-fc4c-4bd1-8dc0-9f24646064b8
    &BangoTransactionId=1078692145
    &TransactionMethods=USA_TMOBILE%2cT-Mobile+USA%2cTESTPAY%2cTest+Pay
    &BillingConfigurationId=218240
    &MozSignature=
    c2cf7b937720c6e41f8b6401696cf7aef56975ebe54f8cee51eff4eb317841af
    &Currency=USD&Network=USA_TMOBILE&Price=0.99&P=
    """
    log.info('Bango success: %s' % request.GET)

    # We should only have OK's coming from Bango, presumably.
    if request.GET.get('ResponseCode') != 'OK':
        return _error(request,
                      msg=('in success(): Invalid Bango response code: %s' %
                           request.GET.get('ResponseCode')))

    if not _record(request):
        return _error(request, msg='Could not record Bango success')

    # Signature verification was successful; fulfill the payment.
    tasks.payment_notify.delay(request.GET.get('MerchantTransactionId'))
    return render(request, 'bango/success.html')


@require_GET
def error(request):
    log.info('Bango error: %s' % request.GET)

    # We should NOT have OK's coming from Bango, presumably.
    if request.GET.get('ResponseCode') == 'OK':
        return _error(request,
                      msg=('in error(): Invalid Bango response code: %s' %
                           request.GET.get('ResponseCode')))

    if not _record(request):
        return _error(request, msg=_('Could not record Bango error'))

    if request.GET.get('ResponseCode') == 'CANCEL':
        return render(request, 'bango/cancel.html')

    return _error(request, msg=_('Received Bango error'))
