from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import (HttpResponseForbidden, HttpResponseNotFound,
                         HttpResponse)
from django.shortcuts import render

from django_paranoia.decorators import require_GET

from lib.solitude.api import client, ProviderHelper
from lib.solitude.constants import PROVIDERS_INVERTED, STATUS_COMPLETED
from webpay.base import dev_messages as msg
from webpay.base.decorators import json_view
from webpay.base.logger import getLogger
from webpay.base.utils import log_cef, system_error
from webpay.pay import tasks

log = getLogger('w.provider')
NoticeClasses = {}


@require_GET
def wait_to_finish(request, provider_name):
    """
    After the payment provider finishes the pay flow, wait for completion.

    The provider redirects here so the UI can poll Solitude until the
    transaction is complete.
    """
    helper = ProviderHelper(provider_name)
    trans_uuid = helper.provider.transaction_from_notice(request.GET)
    if not trans_uuid:
        # This could happen if someone is tampering with the URL or if
        # the payment provider changed their URL parameters.
        log.info('no transaction found for provider {p}; url: {u}'
                 .format(p=helper.provider.name, u=request.get_full_path()))
        return HttpResponseNotFound()

    trans_url = reverse('provider.transaction_status', args=[trans_uuid])

    if settings.SPA_ENABLE:
        return render(request, 'spa/index.html', {
            'transaction_status_url': trans_url,
            'start_view': 'wait-to-finish'})

    return render(request, 'provider/wait-to-finish.html',
                  {'transaction_status_url': trans_url})


@json_view(status_code=203)
@require_GET
def transaction_status(request, transaction_uuid):
    """
    Given a Solitude transaction UUID, return its status.

    This returns a NULL URL for compatibility with another view that
    redirects to begin payment.
    """
    if request.session.get('trans_id') != transaction_uuid:
        log.info('Cannot get transaction status for {t}; session: {s}'
                 .format(t=transaction_uuid, s=repr(request.session)))
        info = ('Transaction query string param {t} did not match '
                'transaction in session'.format(t=transaction_uuid))
        log_cef(info, request, severity=7)
        return HttpResponseForbidden()

    try:
        trans = client.get_transaction(transaction_uuid)
        return {'status': trans['status'], 'url': None,
                'provider': PROVIDERS_INVERTED[trans['provider']]}
    except ObjectDoesNotExist:
        log.info('Cannot get transaction status; not found: {t}'
                 .format(t=transaction_uuid))
        return HttpResponseNotFound()


@require_GET
def success(request, provider_name):
    provider = ProviderHelper(provider_name)
    if provider.name != 'reference':
        raise NotImplementedError(
            'only the reference provider is implemented so far')

    try:
        transaction_id = provider.prepare_notice(request)
    except msg.DevMessage as m:
        return system_error(request, code=m.code)

    tasks.payment_notify.delay(transaction_id)
    return render(request, 'provider/success.html')


@require_GET
def error(request, provider_name):
    provider = ProviderHelper(provider_name)
    if provider.name != 'reference':
        raise NotImplementedError(
            'only the reference provider is implemented so far')

    try:
        provider.prepare_notice(request)
    except msg.DevMessage as m:
        return system_error(request, code=m.code)

    # TODO: handle user cancellation, bug 957774.

    log.error('Fatal payment error for {provider}: {code}; query string: {qs}'
              .format(provider=provider.name,
                      code=request.GET.get('ResponseCode'),
                      qs=request.GET))
    return system_error(request, code=msg.EXT_ERROR)


@require_GET
def notification(request, provider_name):
    """
    Handle server to server notification responses.
    """
    provider = ProviderHelper(provider_name)

    try:
        transaction_uuid = provider.server_notification(request)
    except msg.DevMessage as m:
        return HttpResponse(m.code, status=502)

    trans = client.get_transaction(transaction_uuid)
    log.info('Processing notification for transaction {t}; status={s}'
             .format(t=transaction_uuid, s=trans['status']))
    if trans['status'] == STATUS_COMPLETED:
        tasks.payment_notify.delay(transaction_uuid)

    return HttpResponse('OK')
