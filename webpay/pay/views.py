from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET

import commonware.log
from moz_inapp_pay.exc import InvalidJWT, RequestExpired
from moz_inapp_pay.verify import verify_jwt
from session_csrf import anonymous_csrf_exempt
from tower import ugettext as _

from forms import VerifyForm

log = commonware.log.getLogger('w.pay')


def _error(request, msg='', exception=None):
    external = _('Error processing that request.')
    if settings.VERBOSE_LOGGING:
        if exception:
            msg = u'%s: %s' % (exception.__class__.__name__, exception)
        if msg:
            external = msg
    return render(request, 'pay/verify.html', {'error': external}, status=400)


@anonymous_csrf_exempt
@require_GET
def verify(request):
    form = VerifyForm(request.GET)
    if not form.is_valid():
        return _error(request, msg=form.errors.as_text())

    try:
        verify_jwt(form.cleaned_data['req'],
                   settings.DOMAIN,  # JWT audience.
                   form.secret,
                   required_keys=('request.price',  # An array of
                                                    # price/currency
                                  'request.name',
                                  'request.description'))
    except (TypeError, InvalidJWT, RequestExpired), exc:
        log.exception('calling verify_jwt')
        return _error(request, exception=exc)

    return render(request, 'pay/verify.html')
