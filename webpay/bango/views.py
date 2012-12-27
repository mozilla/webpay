from django import http
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET

import commonware.log

from lib.solitude.api import client
from lib.solitude.constants import STATUS_COMPLETED
from webpay.pay import tasks

log = commonware.log.getLogger('w.bango')


@require_GET
def success(request):
    if 'trans_id' not in request.session:
        return http.HttpResponseBadRequest()
    # Simulate app purchase!
    # TODO(Kumar): fixme. See bug 795143
    if settings.FAKE_PAY_COMPLETE:
        simulated = True
        log.warning('Completing fake transaction without checking signature')
        client.generic.transaction.patch(uuid=['trans_id'],
                                         status=STATUS_COMPLETED)
        tasks.payment_notify.delay(request.session['trans_id'])
    else:
        simulated = False
    return render(request, 'bango/success.html', {'simulated': simulated})


@require_GET
def error(request):
    log.info('Bango error: %s' % request.GET)
    return render(request, 'bango/error.html', {})
