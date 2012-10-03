import sys
import traceback

from django import http
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET

import commonware.log

from moz_inapp_pay.exc import InvalidJWT, RequestExpired
from moz_inapp_pay.verify import verify_jwt
from session_csrf import anonymous_csrf_exempt
from tower import ugettext as _

log = commonware.log.getLogger('w.pay')


@anonymous_csrf_exempt
@require_GET
def verify(request):
    data = request.GET.get('req', '')
    try:
        res = verify_jwt(data, settings.KEY, settings.SECRET)
    except (TypeError, InvalidJWT, RequestExpired):
        error = _('Error parsing JWT')
        log.error(error, exc_info=True)
        if settings.DEBUG:
            error = '\n'.join(traceback.format_exception(*sys.exc_info()))
        return render(request, 'pay/verify.html',
                      {'error': error}, status=400)
    return render(request, 'pay/verify.html')
