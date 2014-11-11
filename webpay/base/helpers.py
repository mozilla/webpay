from urllib import urlencode
import json as jsonlib
import urlparse
import uuid

from django.conf import settings

import jinja2
from jingo import register



@register.filter
def urlparams(url_, hash=None, **query):
    """
    Add a fragment and/or query paramaters to a URL.

    New query params will be appended to exising parameters, except duplicate
    names, which will be replaced.
    """
    url = urlparse.urlparse(url_)
    fragment = hash if hash is not None else url.fragment

    # Use dict(parse_qsl) so we don't get lists of values.
    q = url.query
    query_dict = dict(urlparse.parse_qsl(q)) if q else {}
    query_dict.update((k, v) for k, v in query.items())

    query_string = urlencode([(k, v) for k, v in query_dict.items()
                             if v is not None])
    new = urlparse.ParseResult(url.scheme, url.netloc, url.path, url.params,
                               query_string, fragment)
    return new.geturl()


@register.function
@jinja2.contextfunction
def media(context, url, key='MEDIA_URL'):
    """Get a MEDIA_URL link with a cache buster querystring."""
    if url.endswith('.js'):
        build = context['BUILD_ID_JS']
    elif url.endswith('.css'):
        build = context['BUILD_ID_CSS']
    else:
        build = context['BUILD_ID_IMG']
    return context[key] + urlparams(url, b=build)


@register.function
@jinja2.contextfunction
def static(context, url):
    """Get a STATIC_URL link with a cache buster querystring."""
    return media(context, url, 'STATIC_URL')


@register.function
def spartacus_build_id():
    # Avoid circular import.
    from webpay.base import utils
    return utils.spartacus_build_id()


@register.function
def spartacus_static(path):
    build_id = spartacus_build_id()
    url = settings.SPARTACUS_STATIC + path
    if build_id is not None:
        url += '?bust=' + build_id
    return url


@register.filter
def absolutify(url, site=None):
    """Takes a URL and prepends the SITE_URL"""
    if url.startswith('http'):
        return url
    else:
        if site:
            return site + url
        return settings.SITE_URL + url


@register.filter
def json(s):
    return jsonlib.dumps(s)


def fxa_auth_info(request):
    if not request.session.get('fxa-state'):
        request.session['fxa-state'] = uuid.uuid4().hex
    state = request.session['fxa-state']
    return (state,
            urlparams(
                urlparse.urljoin(settings.FXA_OAUTH_URL,
                                 'v1/authorization'),
                client_id=settings.FXA_CLIENT_ID,
                state=state,
                scope='profile'))

