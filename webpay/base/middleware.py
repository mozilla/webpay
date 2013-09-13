import json
import sys
import traceback
import urlparse

from django.conf import settings
from django.utils.cache import patch_vary_headers
from django.utils.translation.trans_real import parse_accept_lang_header

import tower
from csp.middleware import CSPMiddleware as BaseCSPMiddleware

from webpay.base.logger import getLogger
from webpay.base.utils import log_cef

log = getLogger('w.middleware')


class LogJSONerror:
    """
    If the exception has JSON content, log the JSON message.
    This is intended to catch and log Solitude error messages
    such as form errors for 400 errors.
    """
    def process_exception(self, request, exception):
        etype = type(exception)
        if hasattr(etype, '__name__'):
            etype = etype.__name__
        if hasattr(exception, 'content'):
            try:
                log.error('%s: %s: JSON: %s'
                          % (etype, exception,
                             json.loads(exception.content)))
            except (TypeError, ValueError):
                log.error('%s: %s: %s... (not JSON content)'
                          % (etype, exception,
                             str(exception.content)[0:50]))


class LogExceptionsMiddleware:
    """
    Logs any exception to the console.

    This is useful for development when testing out Ajax calls that
    would not otherwise show the Django debug page.
    """
    def process_exception(self, request, exception):
        traceback.print_exception(*sys.exc_info())


class LocaleMiddleware(object):
    """
    1. Search for the locale.
    2. Save it in the request.
    """
    def __init__(self):
        self.locale_from_accept = False

    def get_language(self, request):
        """
        Return a locale code we support on the site using the
        user's Accept-Language header to determine which is best. This
        mostly follows the RFCs but read bug 439568 for details.
        """
        if request.META.get('HTTP_ACCEPT_LANGUAGE'):
            best = self.get_best_language(
                            request.META['HTTP_ACCEPT_LANGUAGE'])
            if best:
                return best
        return settings.LANGUAGE_CODE

    def get_best_language(self, accept_lang):
        """
        Given an Accept-Language header, return the best-matching language.
        """
        LUM = settings.LANGUAGE_URL_MAP
        langs = LUM.copy()
        langs.update((k.split('-')[0], v) for k, v in LUM.items() if
                      k.split('-')[0] not in langs)
        ranked = parse_accept_lang_header(accept_lang)
        for lang, _ in ranked:
            lang = lang.lower()
            if lang in langs:
                return langs[lang]
            pre = lang.split('-')[0]
            if pre in langs:
                return langs[pre]
        # Could not find an acceptable language.
        return False

    def find_from_input(self, lang):
        """
        Return a supported locale given user input.

        When not supported, returns the default locale.
        """
        if lang in settings.LANGUAGE_URL_MAP:
            return settings.LANGUAGE_URL_MAP[lang]
        else:
            # en-xx -> en-US, en-GB, ...
            supported = [settings.LANGUAGE_URL_MAP[x] for
                         x in settings.LANGUAGE_URL_MAP if
                         x.split('-', 1)[0] == lang.lower().split('-', 1)[0]]
            if len(supported):
                log.info('mapped locale {0} -> {1}'.format(lang, supported[0]))
                return supported[0]

        log.info('unsupported locale: {0}'.format(lang))
        return settings.LANGUAGE_CODE

    def process_request(self, request):
        self.locale_from_accept = False
        if 'lang' in request.GET:
            locale = self.find_from_input(request.GET['lang'])
        else:
            locale = self.get_language(request)
            if locale:
                self.locale_from_accept = True
        # TODO(Kumar) set/check cookie?
        request.locale = locale
        tower.activate(locale)

    def process_response(self, request, response):
        if self.locale_from_accept:
            patch_vary_headers(response, ['Accept-Language'])
        return response


class CEFMiddleware(object):

    def process_request(self, request):
        # Log all requests to cef.
        log_cef('webpay:request', request)

    def process_exception(self, request, exception):
        # We'll log the exceptions too with more severity.
        log_cef(exception.__class__.__name__, request, severity=8)


class CSPMiddleware(BaseCSPMiddleware):

    def process_response(self, request, response):
        # STATIC_URL often ends in a /, but this will ensure if gets changed
        # then it shouldn't break CSP.
        parsed = urlparse.urlparse(settings.STATIC_URL)
        static = '{0}://{1}'.format(parsed.scheme, parsed.netloc)
        # Add these in at the last minute so that we get the correct
        # STATIC_URL from the settings files.
        response._csp_update = {
            'font-src': (static,), 'img-src': (static,),
            'script-src': (static,), 'style-src': (static,),
        }
        return super(CSPMiddleware, self).process_response(request, response)
