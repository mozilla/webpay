import os
import json
import urlparse

from django import http
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_POST

from curling.lib import HttpClientError
from django_browserid import (BrowserIDBackend,
                              get_audience as get_aud_from_request)
from requests_oauthlib import OAuth2Session
from session_csrf import anonymous_csrf_exempt

from lib.marketplace.api import client as mkt_client
from webpay.base.decorators import json_view
from webpay.base.logger import getLogger
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


def native_fxa_authenticate(audience, assertion):
    url = settings.NATIVE_FXA_VERIFICATION_URL
    log.info('verifying Native FxA assertion. url: %s, audience: %s, '
             'assertion: %s' % (url, audience, assertion))

    v = BrowserIDBackend().get_verifier()
    v.verification_service_url = url
    result = v.verify(assertion, audience, url=url)
    if result:
        log.info('Native FxA assertion ok: %s' % result)
        if (result._response.get('issuer') == settings.NATIVE_FXA_ISSUER and
           'fxa-verifiedEmail' in result._response.get('idpClaims', {})):
            return result._response['idpClaims']['fxa-verifiedEmail']
        else:
            return result._response.get('email')


@anonymous_csrf_exempt
@require_POST
@json_view
def reverify(request):
    audience = get_audience(request)
    assertion = request.POST.get('assertion')
    email = native_fxa_authenticate(audience, assertion)
    log.info('Reverify got result: %s' % email)
    if email:
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
    audience = get_audience(request)
    assertion = request.POST.get('assertion')
    email = native_fxa_authenticate(audience, assertion)
    if email:
        store_mkt_permissions(request, email, assertion, audience)
        user_uuid = set_user(request, email)

        redirect_url = check_pin_status(request)

        return {
            'needs_redirect': redirect_url is not None,
            'redirect_url': redirect_url,
            'user_hash': user_uuid
        }
    else:
        log.error('Native FxA assertion failed.')

    request.session.flush()
    return http.HttpResponseBadRequest()


def denied(request):
    return render(request, '403.html', status=403)


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
                  .post(dict(assertion=assertion, audience=audience,
                             is_mobile=True)))
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


def get_fxa_session(**kwargs):
    if settings.DEBUG:
        # In DEBUG mode, don't require HTTPS for FxA oauth redirects.
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    return OAuth2Session(
        settings.FXA_CLIENT_ID,
        scope=u'profile',
        **kwargs)


def _fxa_authorize(fxa, client_secret, request, auth_response):
    token = fxa.fetch_token(
        urlparse.urljoin(settings.FXA_OAUTH_URL, 'v1/token'),
        authorization_response=auth_response,
        client_secret=client_secret)
    res = fxa.post(
        urlparse.urljoin(settings.FXA_OAUTH_URL, 'v1/verify'),
        data=json.dumps({'token': token['access_token']}),
        headers={'Content-Type': 'application/json'})
    return res.json()


@anonymous_csrf_exempt
@json_view
def fxa_login(request):
    session = get_fxa_session(state=request.POST.get('state'))
    data = _fxa_authorize(
        session,
        settings.FXA_CLIENT_SECRET,
        request,
        request.POST.get('auth_response'))
    log.info("FxA login response:" + repr(data,))
    user_hash = set_user(request, data['email'], verified=True)
    return {'user_hash': user_hash, 'user_email': data['email']}
