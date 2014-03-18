import re
import time

from django import http
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.shortcuts import render
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
from webpay.pin.utils import check_pin_status

from lib.marketplace.api import client as marketplace, UnknownPricePoint
from lib.solitude import constants
from lib.solitude.api import client as solitude, ProviderHelper
from lib.solitude.exceptions import ResourceModified

from . import tasks
from .forms import VerifyForm, NetCodeForm
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
            required_keys=('request.id',
                           'request.pricePoint',  # A price tier we'll lookup.
                           'request.name',
                           'request.description',
                           'request.postbackURL',
                           'request.chargebackURL'))
    except RequestExpired, exc:
        er = msg.EXPIRED_JWT
    except InvalidJWT, exc:
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
    notes['issuer_key'] = form.key
    request.session['notes'] = notes
    tx = trans_id()
    log.info('Generated new transaction ID: {tx}'.format(tx=tx))
    request.session['trans_id'] = tx


@require_POST
@json_view
def configure_transaction(request):
    """Configures the transaction to save time later.

    This is called from the client so that it can provide
    MCC/MNC at the same time.

    * When configure_transaction fails this will return a 400
      TRANS_CONFIG_FAILED

    """

    form = NetCodeForm(request.POST)
    sess = request.session

    mcc = None
    mnc = None
    if form.is_valid():
        mcc = form.cleaned_data['mcc']
        mnc = form.cleaned_data['mnc']
        log.info('Client detected network: mcc={mcc}, mnc={mnc}'
                 .format(mcc=mcc, mnc=mnc))

    if settings.SIMULATED_NETWORK:
        mcc = settings.SIMULATED_NETWORK['mcc']
        mnc = settings.SIMULATED_NETWORK['mnc']
        log.warning('OVERRIDING detected network with: mcc={mcc}, mnc={mnc}'
                    .format(mcc=mcc, mnc=mnc))

    notes = sess.get('notes', {})
    if mcc and mnc:
        notes['network'] = {'mnc': mnc, 'mcc': mcc}
    else:
        # Reset network state to avoid leakage from previous states.
        notes['network'] = {}
    sess['notes'] = notes
    log.info('Added mcc/mnc to session: '
             '{network}'.format(network=notes['network']))

    log.info('configuring transaction {0} from client'
             .format(sess.get('trans_id')))

    if not tasks.configure_transaction(request):
        log.error('Configuring transaction failed.')
        return system_error(request, code=msg.TRANS_CONFIG_FAILED)
    else:
        return {'status': 'ok'}


def index(request):
    """Hand off either lobby or serving Spartacus depending on settings."""
    if settings.ENABLE_SPA:
        from webpay.spa.views import index as spa_index
        return spa_index(request)
    else:
        return lobby(request)


@anonymous_csrf_exempt
@require_GET
def lobby(request):
    sess = request.session
    have_jwt = bool(request.GET.get('req'))

    log.info('starting from JWT? {have_jwt}'.format(have_jwt=have_jwt))
    if have_jwt:
        # If it returns a response there was likely
        # an error and we should return it.
        res = process_pay_req(request)
        if isinstance(res, http.HttpResponse):
            return res
    elif settings.TEST_PIN_UI:
        # This won't get you very far but it lets you create/enter PINs
        # and stops a traceback after that.
        sess['trans_id'] = trans_id()

    pin_form = VerifyPinForm()

    if sess.get('uuid'):
        auth_utils.update_session(request, sess.get('uuid'), False)

        redirect_url = check_pin_status(request)
        if redirect_url is not None:
            return http.HttpResponseRedirect(
                '{0}?next={1}'.format(reverse('pay.bounce'), redirect_url)
            )

    # If the buyer closed the trusted UI during reset flow, we want to unset
    # the reset pin flag. They can hit the forgot pin button if they still
    # don't remember their pin.
    if sess.get('uuid_needs_pin_reset'):
        try:
            solitude.set_needs_pin_reset(sess['uuid'], False)
        except ResourceModified:
            return system_error(request, code=msg.RESOURCE_MODIFIED)
        sess['uuid_needs_pin_reset'] = False

    if sess.get('is_simulation', False):
        sim_req = sess['notes']['pay_request']['request']['simulate']
        log.info('Starting simulate %s for %s'
                 % (sim_req, sess['notes']['issuer_key']))
        return render(request, 'pay/simulate.html', {
            'simulate': sim_req
        })

    return render(request, 'pay/lobby.html', {
        'action': reverse('pin.verify'),
        'form': pin_form,
        'title': _('Enter Pin'),
        'track_cancel': {
            'action': 'pin cancel',
            'label': 'Pin Entry Page',
        },
    })


@require_GET
def bounce(request):
    next = request.GET.get('next')
    if not next or not next.startswith('/mozpay/'):
        return http.HttpResponseForbidden()
    return render(request, 'pay/bounce.html', {
        'next': next
    })


@require_POST
def simulate(request):
    if not request.session.get('is_simulation', False):
        log.info('Request to simulate without a valid session')
        return http.HttpResponseForbidden()

    tasks.simulate_notify.delay(request.session['notes']['issuer_key'],
                                request.session['notes']['pay_request'])
    return render(request, 'pay/simulate_done.html', {})


@user_can_simulate
def super_simulate(request):
    if not settings.ALLOW_ADMIN_SIMULATIONS:
        return http.HttpResponseForbidden()
    if request.method == 'POST':
        try:
            trans = solitude.get_transaction(request.session['trans_id'])
        except ObjectDoesNotExist:
            # If this happens a lot and the celery task is just slow,
            # we might need to make a polling loop.
            raise ValueError('Cannot simulate transaction {0}, not configured'
                             .format(request.session.get['trans_id']))
        # TODO: patch solitude to mark this as a super-simulated transaction.

        req = trans['notes']['pay_request']
        # TODO: support simulating refunds.
        req['request']['simulate'] = {'result': 'postback'}
        tasks.simulate_notify.delay(trans['notes']['issuer_key'], req)

        return render(request, 'pay/simulate_done.html', {})

    return render(request, 'pay/super_simulate.html')


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

    The transaction was started previously during the buy flow in the
    background from webpay.pay.tasks.

    Serve JS that polls for transaction state.
    When ready, redirect to the Bango payment URL using
    the generated billing configuration ID.
    """
    trans_id = request.session.get('trans_id', None)
    if not trans_id:
        # This seems like a seriously problem but maybe there is just a race
        # condition. If we see a lot of these in the logs it means the
        # payment will never complete so we should keep an eye on it.
        log.error('wait_to_start() session trans_id {t} was None'
                  .format(t=trans_id))
    try:
        statsd.incr('purchase.payment_time.retry')
        with statsd.timer('purchase.payment_time.get_transation'):
            trans = solitude.get_transaction(trans_id)
    except ObjectDoesNotExist:
        trans = {'status': None}

    if trans['status'] in constants.STATUS_ENDED:
        statsd.incr('purchase.payment_time.failure')
        log.exception('Attempt to restart finished transaction {0} '
                      'with status {1}'.format(trans_id, trans['status']))
        return system_error(request, code=msg.TRANS_ENDED)

    if trans['status'] == constants.STATUS_PENDING:
        statsd.incr('purchase.payment_time.success')
        payment_start = request.session.get('payment_start', False)
        if payment_start:
            delta = int((time.time() - float(payment_start)) * 1000)
            statsd.timing('purchase.payment_time.duration', delta)
        # Dump any messages so we don't show them later.
        clear_messages(request)
        # The transaction is ready; no need to wait for it.
        url = get_payment_url(trans)
        log.info('immediately redirecting to payment URL {url} '
                 'for trans {tr}'.format(url=url, tr=trans))
        return http.HttpResponseRedirect(url)
    return render(request, 'pay/wait-to-start.html')


@user_verified
@json_view
@require_GET
def trans_start_url(request):
    """
    JSON handler to get the Bango payment URL to start a transaction.
    """
    try:
        statsd.incr('purchase.payment_time.retry')
        with statsd.timer('purchase.payment_time.get_transaction'):
            trans = solitude.get_transaction(request.session['trans_id'])
    except ObjectDoesNotExist:
        log.error('trans_start_url() transaction does not exist: {t}'
                  .format(t=request.session['trans_id']))
        trans = {'status': None}

    data = {'url': None, 'status': trans['status']}
    if trans['status'] == constants.STATUS_PENDING:
        statsd.incr('purchase.payment_time.success')
        payment_start = request.session.get('payment_start', False)
        if payment_start:
            delta = int((time.time() - float(payment_start)) * 1000)
            statsd.timing('purchase.payment_time.duration', delta)
        url = get_payment_url(trans)
        log.info('async call got payment URL {url} for trans {tr}'
                 .format(url=url, tr=trans))
        data['url'] = url
    return data


def _callback_url(request, is_success):
    status = is_success and 'success' or 'error'
    signed_notice = request.POST['signed_notice']
    statsd.incr('purchase.payment_{0}_callback.received'.format(status))

    # This is currently only used by Bango and Zippy.
    # Future providers should probably get added to the notification
    # abstraction in provider/views.py
    provider = ProviderHelper(settings.PAYMENT_PROVIDER)

    if provider.is_callback_token_valid(signed_notice):
        statsd.incr('purchase.payment_{0}_callback.ok'.format(status))
        log.info('Callback {0} token was valid.'.format(status))
        querystring = http.QueryDict(signed_notice)
        if 'ext_transaction_id' in querystring:
            ext_transaction_id = querystring['ext_transaction_id']
            if is_success:
                tasks.payment_notify.delay(ext_transaction_id)
            else:
                tasks.chargeback_notify.delay(ext_transaction_id)
            return http.HttpResponse(status=204)
        else:
            statsd.incr('purchase.payment_{0}_callback.incomplete'
                        ''.format(status))
            log.error('Callback {0} token was incomplete: '
                      '{1}'.format(status, querystring))
    else:
        statsd.incr('purchase.payment_{0}_callback.fail'.format(status))
        log.error('Callback {0} token was invalid: '
                  '{1}'.format(status, signed_notice))
    return http.HttpResponseBadRequest()


@require_POST
def callback_success_url(request):
    """
    Hit by the provider to confirm a success of a transaction
    in case of an interruption in the payment process.
    """
    return _callback_url(request, is_success=True)


@require_POST
def callback_error_url(request):
    """
    Hit by the provider to confirm a failure of a transaction
    in case of an interruption in the payment process.
    """
    return _callback_url(request, is_success=False)


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
        for k, v in req['request']['locales'].items():
            d = _trim(v['description'])
            req['request']['locales'][k]['description'] = d


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


def get_payment_url(transaction):
    """
    Given a Solitude transaction object, return a URL to start the payment
    flow for this provider.
    """
    # A transaction pay_url is configured at the time that a
    # transaction is started.
    url = transaction['pay_url']
    log.info('Start pay provider payflow "{pr}" for '
             'transaction {tr} at: {url}'
             .format(pr=transaction.get('provider'), url=url,
                     tr=transaction.get('uuid')))
    return url
