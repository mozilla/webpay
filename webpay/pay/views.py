from decimal import Decimal
import json

from django import http
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

import commonware.log
from moz_inapp_pay.exc import InvalidJWT, RequestExpired
from moz_inapp_pay.verify import verify_jwt
from session_csrf import anonymous_csrf_exempt
from tower import ugettext as _

from webpay.pin.forms import VerifyPinForm
from . import tasks
from .forms import VerifyForm
from .models import (Issuer, Transaction, TRANS_STATE_PENDING,
                     TRANS_STATE_COMPLETED)

log = commonware.log.getLogger('w.pay')


def _error(request, msg='', exception=None):
    external = _('Error processing that request.')
    if settings.VERBOSE_LOGGING:
        if exception:
            msg = u'%s: %s' % (exception.__class__.__name__, exception)
        if msg:
            external = msg
    return render(request, 'pay/error.html', {'error': external}, status=400)


@anonymous_csrf_exempt
@require_GET
def lobby(request):
    form = VerifyForm(request.GET)
    if not form.is_valid():
        return _error(request, msg=form.errors.as_text())
    pin_form = VerifyPinForm()

    try:
        pay_req = verify_jwt(
            form.cleaned_data['req'],
            settings.DOMAIN,  # JWT audience.
            form.secret,
            required_keys=('request.price',  # An array of
                                             # price/currency
                           'request.name',
                           'request.description'))
    except (TypeError, InvalidJWT, RequestExpired), exc:
        log.exception('calling verify_jwt')
        return _error(request, exception=exc)

    # Simulate app purchase!
    # TODO(Kumar): fixme
    try:
        iss = Issuer.objects.get(issuer_key=form.key)
    except Issuer.DoesNotExist:
        iss = None  # marketplace
    trans = Transaction.create(
       state=TRANS_STATE_PENDING,
       issuer=iss,
       issuer_key=form.key,
       amount=Decimal(pay_req['request']['price'][0]['amount']),
       currency=pay_req['request']['price'][0]['currency'],
       name=pay_req['request']['name'],
       description=pay_req['request']['description'],
       json_request=json.dumps(pay_req))

    request.session['trans_id'] = trans.pk
    return render(request, 'pay/lobby.html', {'pin_form': pin_form})


@anonymous_csrf_exempt
@require_POST
def complete(request):
    if 'trans_id' not in request.session:
        return http.HttpResponseBadRequest()
    # Simulate app purchase!
    # TODO(Kumar): fixme
    if settings.FAKE_PAYMENTS:
        trans = Transaction.objects.get(pk=request.session['trans_id'])
        trans.state = TRANS_STATE_COMPLETED
        trans.save()
        tasks.payment_notify.delay(trans.pk)
    return render(request, 'pay/complete.html')


@anonymous_csrf_exempt
@require_GET
def fakepay(request):
    if not settings.FAKE_PAYMENTS:
        return http.HttpResponseForbidden()
    return render(request, 'pay/fakepay.html')
