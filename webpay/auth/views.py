import os
import json
import urlparse
from datetime import datetime

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
from webpay.base.utils import gmtime
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

    # Set the starting timestamp of the reset for later use when verifying
    # their Firefox Accounts password entry.
    start_ts = gmtime()
    request.session['user_reset'] = {'start_ts': start_ts}
    log.info('PIN reset start: {r}'
             .format(r=datetime.utcfromtimestamp(start_ts)))

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
        return {'user_hash': reverified_user, 'user_email': email}

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

        return {
            'user_email': email,
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


def _process_fxa_auth_ts(token, request):
    """
    Process and store the last FxA authentication time for this token.
    """
    fxa_auth_ts = token.get('auth_at')
    if not isinstance(fxa_auth_ts, (int, float)):
        log.info('Got non-numeric FxA auth_at timestamp: {a}'
                 .format(a=fxa_auth_ts))
        fxa_auth_ts = None
    if not fxa_auth_ts:
        raise ValueError(
            'Cannot safely reset PIN, FxA token "auth_at" value '
            'was invalid; token: {t}'.format(t=token))
    request.session.setdefault('user_reset', {})
    request.session['user_reset']['fxa_auth_ts'] = fxa_auth_ts

    start_ts = request.session['user_reset'].get('start_ts')
    log.info('FxA auth_at: "{a}"; PIN reset start: "{r}"'
             .format(r=start_ts and datetime.utcfromtimestamp(start_ts),
                     a=datetime.utcfromtimestamp(fxa_auth_ts)))


def _fxa_authorize(fxa, client_secret, request, auth_response):
    """
    Fetch and verify an FxA oauth token.

    Returns a tuple of JSON dicts: (verification_response, token_response)
    """
    log.info('fetching FxA token from auth_response: "{a}"'
             .format(a=auth_response))
    token = fxa.fetch_token(
        urlparse.urljoin(settings.FXA_OAUTH_URL, 'v1/token'),
        authorization_response=auth_response,
        client_secret=client_secret)
    res = fxa.post(
        urlparse.urljoin(settings.FXA_OAUTH_URL, 'v1/verify'),
        data=json.dumps({'token': token['access_token']}),
        headers={'Content-Type': 'application/json'})
    return res.json(), token


@anonymous_csrf_exempt
@json_view
def fxa_login(request):
    session = get_fxa_session(state=request.POST.get('state'))
    result, token = _fxa_authorize(
        session,
        settings.FXA_CLIENT_SECRET,
        request,
        request.POST.get('auth_response'))

    log.info("FxA token verification response. result={r}; token={t}"
             .format(r=result, t=token))

    if result.get('error'):
        # All errors look like:
        # https://github.com/mozilla/fxa-oauth-server/blob/master
        # /docs/api.md#errors
        log.info('FxA login error: {r}'.format(r=result))
        return http.HttpResponseForbidden()

    _process_fxa_auth_ts(token, request)
    user_hash = set_user(request, result['email'], verified=False)

    return {'user_hash': user_hash, 'user_email': result['email'],
            'super_powers': request.session.get('super_powers', False)}
