from urllib import urlencode
import urlparse

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
