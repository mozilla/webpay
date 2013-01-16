import uuid

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
from webpay.pin.utils import pin_recently_entered

from lib.marketplace.api import (client as marketplace, HttpClientError,
                                 TierNotFound)
from lib.solitude import constants
from lib.solitude.api import client as solitude

from . import tasks
from .forms import VerifyForm
from .models import Issuer

log = commonware.log.getLogger('w.pay')


def _error(request, msg='', exception=None):
    external = _('There was an error processing that request.')
    if settings.VERBOSE_LOGGING:
        if exception:
            msg = u'%s: %s' % (exception.__class__.__name__, exception)
        if msg:
            external = msg
    return render(request, 'pay/error.html', {'error': external}, status=400)


def process_pay_req(request):
    form = VerifyForm(request.GET)
    if not form.is_valid():
        return _error(request, msg=form.errors.as_text())

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
        marketplace.get_price(pay_req['request']['pricePoint'])
    except (TierNotFound, HttpClientError), exc:
        log.exception('calling verifying tier')
        return _error(request, exception=exc)

    try:
        iss = Issuer.objects.get(issuer_key=form.key)
    except Issuer.DoesNotExist:
        iss = None  # marketplace

    request.session['notes'] = {'pay_request': pay_req,
                                'issuer': iss.pk if iss else None,
                                'issuer_key': form.key}
    request.session['trans_id'] = 'webpay:%s' % uuid.uuid4()

    # Before we verify the user's PIN let's save some
    # time and get the transaction configured via Bango in the
    # background.
    if not settings.FAKE_PAYMENTS:
        tasks.start_pay.delay(request.session['trans_id'],
                              request.session['notes'])


@anonymous_csrf_exempt
@require_GET
def lobby(request):
    if request.GET.get('req'):
        # If it returns a response there was likely
        # an error and we should return it.
        res = process_pay_req(request)
        if isinstance(res, http.HttpResponse):
            return res
    elif not 'notes' in request.session:
        return _error(request, msg='req is required')

    pin_form = VerifyPinForm()
    pin_form.pin_recently_entered = pin_recently_entered(request)

    return render(request, 'pay/lobby.html', {'form': pin_form,
                  'title': _('Enter your PIN:')})


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
    try:
        trans = solitude.get_transaction(request.session['trans_id'])
    except ValueError:
        trans = {'status': None}
    if trans['status'] == constants.STATUS_PENDING:
        # The transaction is ready; no need to wait for it.
        return http.HttpResponseRedirect(
            settings.BANGO_PAY_URL % trans['uid_pay'])
    return render(request, 'pay/wait-to-start.html')


@user_verified
@json_view
@require_GET
def trans_start_url(request):
    """
    JSON handler to get the Bango payment URL to start a transaction.
    """
    try:
        trans = solitude.get_transaction(request.session['trans_id'])
    except ValueError:
        trans = {'status': None}
    data = {'url': None, 'status': trans['status']}
    if trans['status'] == constants.STATUS_PENDING:
        data['url'] = settings.BANGO_PAY_URL % trans['uid_pay']
    # TODO(Wraithan): We should catch if a user is trying to restart an expired
    #                 or completed transaction. (bug 829750).
    #                 This will timeout in the client until then.
    return data
