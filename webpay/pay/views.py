import json

from django import http
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET

import commonware.log
from moz_inapp_pay.exc import InvalidJWT, RequestExpired
from moz_inapp_pay.verify import verify_jwt
from session_csrf import anonymous_csrf_exempt
from tower import ugettext as _

from webpay.auth.decorators import user_verified
from webpay.base.decorators import json_view
from webpay.pin.forms import VerifyPinForm

from lib.marketplace.api import client, HttpClientError, TierNotFound

from . import tasks
from .forms import VerifyForm
from .models import (Issuer, Transaction, TRANS_STATE_PENDING,
                     TRANS_STATE_READY)

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
            required_keys=('request.id',
                           'request.pricePoint',  # A price tier we'll lookup.
                           'request.name',
                           'request.description'))
    except (TypeError, InvalidJWT, RequestExpired), exc:
        log.exception('calling verify_jwt')
        return _error(request, exception=exc)

    # Assert pricePoint is valid.
    try:
        client.get_price(pay_req['request']['pricePoint'])
    except (TierNotFound, HttpClientError), exc:
        log.exception('calling verifying tier')
        return _error(request, exception=exc)

    try:
        iss = Issuer.objects.get(issuer_key=form.key)
    except Issuer.DoesNotExist:
        iss = None  # marketplace

    # TODO(Kumar) fix this for reals. See bug 820198.
    desc = pay_req['request']['description']
    if len(desc) > 255:
        desc = desc[0:255]

    trans = Transaction.create(
       state=TRANS_STATE_PENDING,
       issuer=iss,
       issuer_key=form.key,
       product_id=pay_req['request']['id'],
       amount=1,  # Set this temporarily until we remove transactions.
       currency='USD',  # This too.
       name=pay_req['request']['name'],
       description=desc,
       json_request=json.dumps(pay_req))

    request.session['trans_id'] = trans.pk
    request.session['pay_request'] = pay_req

    # Before we verify the user's PIN let's save some
    # time and get the transaction configured via Bango in the
    # background.
    if not settings.FAKE_PAYMENTS:
        tasks.start_pay.delay(request.session['trans_id'],
                              request.session['pay_request'])

    return render(request, 'pay/lobby.html', {'pin_form': pin_form})


@anonymous_csrf_exempt
@require_GET
def fakepay(request):
    if not settings.FAKE_PAYMENTS:
        return http.HttpResponseForbidden()
    return render(request, 'pay/fakepay.html')


@user_verified
@require_GET
def fake_bango_url(request):
    return render(request, 'pay/fake-bango-url.html',
                  {'bill_config_id': request.GET['bcid']})


@user_verified
@require_GET
def wait_to_start(request):
    """
    Wait until the transaction is in a ready state.

    Serve JS that polls for transaction state.
    When ready, redirect to the Bango payment URL using
    the generated billing configuration ID.
    """
    trans = Transaction.objects.get(pk=request.session['trans_id'])
    if trans.state == TRANS_STATE_READY:
        # The transaction is ready; no need to wait for it.
        return http.HttpResponseRedirect(
            settings.BANGO_PAY_URL % trans.bango_config_id)
    return render(request, 'pay/wait-to-start.html')


@user_verified
@json_view
@require_GET
def trans_start_url(request):
    """
    JSON handler to get the Bango payment URL to start a transaction.
    """
    trans = Transaction.objects.get(pk=request.session['trans_id'])
    data = {'url': None, 'state': trans.state}
    if trans.state == TRANS_STATE_READY:
        data['url'] = settings.BANGO_PAY_URL % trans.bango_config_id
    return data
