import json
import sys
import traceback

from django import http
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET

import commonware.log
import jwt
from moz_inapp_pay.exc import InvalidJWT, RequestExpired
from moz_inapp_pay.verify import verify_jwt
from session_csrf import anonymous_csrf_exempt
from tower import ugettext as _

from forms import VerifyForm
from models import InappConfig

log = commonware.log.getLogger('w.pay')


def _error(request, msg=''):
    log.error(msg, exc_info=True)
    external = _('Error processing that request.')
    if settings.VERBOSE_LOGGING:
        external = '\n'.join(traceback.format_exception(*sys.exc_info()))
    return render(request, 'pay/verify.html', {'error': external}, status=400)


@anonymous_csrf_exempt
@require_GET
def verify(request):
    form = VerifyForm(request.GET)
    if not form.is_valid():
        return _error(request, msg=u'Form error')

    try:
        res = verify_jwt(form.cleaned_data['req'],
                         settings.ISSUER,
                         form.secret)
    except (TypeError, InvalidJWT, RequestExpired):
        return _error(request, msg=u'JWT error')

    return render(request, 'pay/verify.html')
