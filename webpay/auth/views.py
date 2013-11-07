from django import http
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_POST

from curling.lib import HttpClientError
from django_browserid import (get_audience as get_aud_from_request,
                              verify as verify_assertion)
from django_browserid.forms import BrowserIDForm
from session_csrf import anonymous_csrf_exempt

from lib.marketplace.api import client as mkt_client
from webpay.base.decorators import json_view
from webpay.base.logger import getLogger
from webpay.pay import tasks as pay_tasks
from webpay.pin.utils import check_pin_status
from .utils import get_uuid, set_user

log = getLogger('w.auth')


@require_POST
def reset_user(request):
    """
    Reset the logged in Persona user.

    This is not meant as a full logout. It's meant to compliment
    navigator.id.logout() so that both Webpay and Persona think the user
    is logged out.
    """
    if 'logged_in_user' in request.session:
        log.info('Resetting Persona user %s'
                 % request.session['logged_in_user'])
        del request.session['logged_in_user']
    if 'mkt_permissions' in request.session:
        # This isn't strictly necessary since permissions are reset on
        # login but it's good for paranoia.
        del request.session['mkt_permissions']
    return http.HttpResponse('OK')


@anonymous_csrf_exempt
@require_POST
@json_view
def reverify(request):
    form = BrowserIDForm(data=request.POST)
    if form.is_valid():
        url = settings.BROWSERID_VERIFICATION_URL
        audience = get_audience(request)
        extra_params = {
            'experimental_forceIssuer': settings.BROWSERID_UNVERIFIED_ISSUER,
            'experimental_forceAuthentication': 'true',
            'experimental_allowUnverified': 'true'
        }

        assertion = form.cleaned_data['assertion']
        log.info('Re-verifying Persona assertion. url: %s, audience: %s, '
                 'extra_params: %s' % (url, audience, extra_params))
        result = verify_assertion(assertion, audience, extra_params)

        log.info('Reverify got result: %s' % result)
        if result:
            email = result.get('unverified-email', result.get('email'))
            store_mkt_permissions(request, email, assertion, audience)
            logged_user = request.session.get('uuid')
            reverified_user = get_uuid(email)
            if logged_user and logged_user != reverified_user:
                log.error('User %r tried to reverify as '
                          'new email: %s' % (logged_user, email))
                return http.HttpResponseBadRequest()

            request.session['was_reverified'] = True
            return {'user_hash': reverified_user}

        log.error('Persona assertion failed.')

    request.session.clear()
    return http.HttpResponseBadRequest()


@anonymous_csrf_exempt
@require_POST
@json_view
def verify(request):
    form = BrowserIDForm(data=request.POST)
    if form.is_valid():
        url = settings.BROWSERID_VERIFICATION_URL
        audience = get_audience(request)
        extra_params = {
            'experimental_forceIssuer': settings.BROWSERID_UNVERIFIED_ISSUER,
            'experimental_allowUnverified': 'true'
        }
        assertion = form.cleaned_data['assertion']
        log.info('verifying Persona assertion. url: %s, audience: %s, '
                 'extra_params: %s, assertion: %s' % (url, audience,
                                                      extra_params, assertion))
        result = verify_assertion(assertion, audience, extra_params)
        if result:
            log.info('Persona assertion ok: %s' % result)
            email = result.get('unverified-email', result.get('email'))
            store_mkt_permissions(request, email, assertion, audience)
            user_uuid = set_user(request, email)

            redirect_url = check_pin_status(request)

            # Before we verify the user's PIN let's save some
            # time and get the transaction configured via Bango in the
            # background.
            log.info('configuring transaction {0} from auth'
                     .format(request.session.get('trans_id')))
            if not pay_tasks.configure_transaction(request):
                log.error('Configuring transaction failed.')

            return {
                'needs_redirect': redirect_url is not None,
                'redirect_url': redirect_url,
                'user_hash': user_uuid
            }

        log.error('Persona assertion failed.')

    request.session.flush()
    return http.HttpResponseBadRequest()


def denied(request):
    return render(request, '403.html')


def get_audience(request):
    if settings.DEV:
        # This is insecure but convenient.
        return get_aud_from_request(request)
    else:
        return settings.SITE_URL


def store_mkt_permissions(request, email, assertion, audience):
    """
    After logging into webpay, try logging into Marketplace with the
    same assertion.

    If successful, store the marketplace user permissions.
    This can be used later to allow elevated privileges, such as simulated
    purchases.

    The marketplace login will only work if the Persona email in webpay
    matches the marketplace one exactly.
    """
    if not settings.ALLOW_ADMIN_SIMULATIONS:
        log.info('admin simulations are disabled')
        return

    permissions = {}
    try:
        result = (mkt_client.api.account.login()
                  .post(dict(assertion=assertion, audience=audience)))
        # e.g. {u'admin': False, u'localizer': False, u'lookup': False,
        #       u'webpay': False, u'reviewer': False, u'developer': False}
        permissions = result['permissions']
        log.info('granting mkt permissions: {0} to user {1}'
                 .format(permissions, email))
    except HttpClientError, exc:
        # This would typically be a 401 -- a non-existent user.
        log.info('Not storing mkt permissions for {0}: {1}: {2}'
                 .format(email, exc.__class__.__name__, exc))

    request.session['mkt_permissions'] = permissions
