import re
import time
import uuid

from django import http
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from django_statsd.clients import statsd
from mozpay.exc import InvalidJWT, RequestExpired
from mozpay.verify import verify_jwt
from session_csrf import anonymous_csrf_exempt
from tower import ugettext as _

from webpay.auth.decorators import user_can_simulate, user_verified
from webpay.auth import utils as auth_utils
from webpay.base import dev_messages as msg
from webpay.base.decorators import json_view
from webpay.base.logger import getLogger
from webpay.base.utils import app_error, custom_error, system_error
from webpay.pin.forms import VerifyPinForm

from lib.marketplace.api import client as marketplace, UnknownPricePoint
from lib.solitude import constants
from lib.solitude.api import client as solitude
from lib.solitude.exceptions import ResourceModified

from . import tasks
from .forms import SuperSimulateForm, VerifyForm, NetCodeForm
from .utils import clear_messages, trans_id, verify_urls

log = getLogger('w.pay')


def process_pay_req(request, data=None):
    data = request.GET if data is None else data
    form = VerifyForm(data)
    if not form.is_valid():
        codes = []
        for erlist in form.errors.values():
            codes.extend(erlist)
        if len(codes) > 1:
            # This will probably break something, like maybe paymentFailed().
            log.error('multiple error codes: {codes}'.format(codes=codes))
        codes = ', '.join(codes)
        return app_error(request, code=codes)

    if (disabled_by_user_agent(request.META.get('HTTP_USER_AGENT', None)) or
            (settings.ONLY_SIMULATIONS and not form.is_simulation)):
        return custom_error(request,
                            _('Payments are temporarily disabled.'),
                            code=msg.PAY_DISABLED, status=503)

    exc = er = None
    try:
        pay_req = verify_jwt(
            form.cleaned_data['req'],
            settings.DOMAIN,  # JWT audience.
            form.secret,
            algorithms=settings.SUPPORTED_JWT_ALGORITHMS,
            required_keys=('request.id',
                           'request.pricePoint',  # A price tier we'll look up.
                           'request.name',
                           'request.description',
                           'request.postbackURL',
                           'request.chargebackURL'))
    except RequestExpired, exc:
        log.debug('exception in mozpay.verify_jwt(): {e}'.format(e=exc))
        er = msg.EXPIRED_JWT
    except InvalidJWT, exc:
        log.debug('exception in mozpay.verify_jwt(): {e}'.format(e=exc))
        er = msg.INVALID_JWT

    if exc:
        log.exception('calling verify_jwt')
        return app_error(request, code=er)

    icon_urls = []
    if pay_req['request'].get('icons'):
        icon_urls = pay_req['request']['icons'].values()
    # Verify that all URLs are valid.
    try:
        verify_urls(pay_req['request']['postbackURL'],
                    pay_req['request']['chargebackURL'],
                    is_simulation=form.is_simulation)
        verify_urls(*icon_urls,
                    is_simulation=form.is_simulation,
                    check_postbacks=False)
    except ValueError, exc:
        log.exception('invalid URLs')
        return app_error(request, code=msg.MALFORMED_URL)

    # Assert pricePoint is valid.
    try:
        marketplace.get_price(pay_req['request']['pricePoint'])
    except UnknownPricePoint:
        log.exception('UnknownPricePoint calling get price_price()')
        return app_error(request, code=msg.BAD_PRICE_POINT)

    _trim_pay_request(pay_req)

    # All validation passed, save state to the session.
    request.session['is_simulation'] = form.is_simulation
    # This is an ephemeral session value, do not rely on it.
    # It gets saved to the solitude transaction so you can access it there.
    # Otherwise it is used for simulations and fake payments.
    notes = request.session.get('notes', {})
    notes['pay_request'] = pay_req
    # The issuer key points to the app that issued the payment request.
    notes['issuer_key'] = form.key
    request.session['notes'] = notes
    tx = trans_id()
    log.info('Generated new transaction ID: {tx}'.format(tx=tx))
    request.session['trans_id'] = tx


@require_POST
@json_view
def configure_transaction(request, data=None):
    """
    Configures a transaction so the user can be redirected to a buy screen.

    This is called from the client so that it can provide
    MCC/MNC at the same time.

    * When configure_transaction fails this will return a 400
      TRANS_CONFIG_FAILED

    """

    form = NetCodeForm(data or request.POST)

    mcc = None
    mnc = None
    if form.is_valid():
        mcc = form.cleaned_data['mcc']
        mnc = form.cleaned_data['mnc']
        log.info('Client detected network: mcc={mcc}, mnc={mnc}'
                 .format(mcc=mcc, mnc=mnc))
    else:
        log.info('Network form was invalid, no codes were applied.')
        log.debug('Network form errors: {e}'.format(e=form.errors.as_text()))

    if settings.SIMULATED_NETWORK:
        mcc = settings.SIMULATED_NETWORK['mcc']
        mnc = settings.SIMULATED_NETWORK['mnc']
        log.warning('OVERRIDING detected network with: mcc={mcc}, mnc={mnc}'
                    .format(mcc=mcc, mnc=mnc))

    is_simulation = request.session.get('is_simulation', False)
    pay_req = request.session.get('notes', {}).get('pay_request')
    payment_required = (
        pay_req['request']['pricePoint'] != '0' if pay_req else True)

    if payment_required:
        was_configured, error_code = tasks.configure_transaction(
            request, mcc=mcc, mnc=mnc)
        if not was_configured and not is_simulation:
            if not error_code:
                error_code = msg.TRANS_CONFIG_FAILED
            log.error('Configuring transaction failed: {er}'
                      .format(er=error_code))
            return system_error(request, code=error_code)
    else:
        solitude_buyer_uuid = request.session['uuid']
        log.info('Notifying for free in-app trans_id={t}; with '
                 'solitude_buyer_uuid={u}'.format(
                     t=request.session['trans_id'], u=solitude_buyer_uuid))
        tasks.free_notify.delay(request.session['notes'], solitude_buyer_uuid)

    sim = pay_req['request']['simulate'] if is_simulation else None
    client_trans_id = 'client-trans:{u}'.format(u=uuid.uuid4())
    log.info('Assigned client trans ID {client_trans} to trans ID {trans}'
             .format(trans=request.session['trans_id'],
                     client_trans=client_trans_id))
    return {'status': 'ok', 'simulation': sim,
            'client_trans_id': client_trans_id,
            'payment_required': payment_required}


def _trim_pay_request(req):

    def _trim(st):
        if len(st) > settings.PRODUCT_DESCRIPTION_LENGTH:
            elip = '...'
            cut = settings.PRODUCT_DESCRIPTION_LENGTH - len(elip)
            st = u'{0}{1}'.format(st[0:cut], elip)
        return st

    # Trim long descriptions so they don't inflate our session cookie
    # size unexpectedly.
    req['request']['description'] = _trim(req['request']['description'])
    if req['request'].get('locales'):
        for slug, locale in req['request']['locales'].items():
            if 'description' in locale:
                desc = _trim(locale['description'])
                req['request']['locales'][slug]['description'] = desc


_android_user_agent = re.compile(r'^Mozilla.*Android.*Gecko.*Firefox')
# 28.1 is unique to Tarako.
# See https://bugzilla.mozilla.org/show_bug.cgi?id=987450
_tarako_user_agent = re.compile(r'Mozilla.*Mobile.*rv:28\.1.*Gecko/28\.1')


def disabled_by_user_agent(user_agent):
    """
    Returns True if payments are disabled for this user agent.
    """
    is_disabled = False
    if not user_agent:
        user_agent = ''

    if not settings.ALLOW_ANDROID_PAYMENTS:
        if _android_user_agent.search(user_agent):
            is_disabled = True
    if not settings.ALLOW_TARAKO_PAYMENTS:
        if _tarako_user_agent.search(user_agent):
            is_disabled = True

    if is_disabled:
        log.info('Disabling payments for this user agent: {ua}'
                 .format(ua=user_agent))

    return is_disabled
