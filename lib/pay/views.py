from django import http
from django.conf import settings
from django.views.decorators.http import require_POST

import commonware.log

from moz_inapp_pay.exc import InvalidJWT, RequestExpired
from moz_inapp_pay.verify import verify_jwt
from session_csrf import anonymous_csrf_exempt

log = commonware.log.getLogger('w.pay')


def error(msg, request):
    log.error(msg, exc_info=True)
    if settings.DEBUG:
        raise
    else:
        return http.HttpResponseBadRequest()

@anonymous_csrf_exempt
@require_POST
def verify(request):
    data = request.body
    try:
        res = verify_jwt(data, settings.KEY, settings.SECRET)
    except (InvalidJWT, RequestExpired):
        return error(u'Failed to parse JWT', error)
    if not res:
        print res
        return http.HttpResponseBadRequest()

    return http.HttpResponse('ok')
