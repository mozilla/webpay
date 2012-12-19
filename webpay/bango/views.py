from django import http
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

import commonware.log

from webpay.pay.models import TRANS_STATE_COMPLETED

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
        trans = Transaction.objects.get(pk=request.session['trans_id'])
        trans.state = TRANS_STATE_COMPLETED
        trans.save()
        tasks.payment_notify.delay(trans.pk)
    else:
        simulated = False
    return render(request, 'bango/success.html', {'simulated': simulated})


@require_GET
def error(request):
    return render(request, 'bango/error.html', {})
