from django.shortcuts import render

from django_paranoia.decorators import require_GET

from lib.solitude.api import ProviderHelper
from webpay.base import dev_messages as msg
from webpay.base.logger import getLogger
from webpay.base.utils import system_error
from webpay.pay import tasks

log = getLogger('w.provider')
NoticeClasses = {}


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
