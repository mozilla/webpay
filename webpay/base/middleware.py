from django.conf import settings
from django.utils.cache import patch_vary_headers
from django.utils.translation.trans_real import parse_accept_lang_header

import tower


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
                return supported[0]
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
