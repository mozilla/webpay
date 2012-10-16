from django import http
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

import commonware.log
from commonware.response.decorators import xframe_allow
from moz_inapp_pay.exc import InvalidJWT, RequestExpired
from moz_inapp_pay.verify import verify_jwt
from session_csrf import anonymous_csrf_exempt
from tower import ugettext as _

from . import tasks
from .forms import VerifyForm

log = commonware.log.getLogger('w.pay')


def _error(request, msg='', exception=None):
    external = _('Error processing that request.')
    if settings.VERBOSE_LOGGING:
        if exception:
            msg = u'%s: %s' % (exception.__class__.__name__, exception)
        if msg:
            external = msg
    return render(request, 'pay/error.html', {'error': external}, status=400)


@anonymous_csrf_exempt
@require_GET
@xframe_allow
def verify(request):
    form = VerifyForm(request.GET)
    if not form.is_valid():
        return _error(request, msg=form.errors.as_text())

    try:
        pay_req = verify_jwt(
            form.cleaned_data['req'],
            settings.DOMAIN,  # JWT audience.
            form.secret,
            required_keys=('request.price',  # An array of
                                             # price/currency
                           'request.name',
                           'request.description'))
    except (TypeError, InvalidJWT, RequestExpired), exc:
        log.exception('calling verify_jwt')
        return _error(request, exception=exc)

    request.session['pay_request'] = pay_req
    return render(request, 'pay/verify.html')


@anonymous_csrf_exempt
@require_POST
@xframe_allow
def complete(request):
    if 'pay_request' not in request.session:
        return http.HttpResponseBadRequest()
    # Simulate app purchase!
    # TODO(Kumar): fixme
    tasks.payment_notify.delay(pay_request=request.session['pay_request'],
                               public_key=settings.KEY)
    return render(request, 'pay/complete.html')
