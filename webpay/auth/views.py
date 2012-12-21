from django import http
from django.core.urlresolvers import reverse
from django.views.decorators.http import require_POST

import commonware.log
from django_browserid import get_audience, verify as verify_assertion
from django_browserid.forms import BrowserIDForm
from session_csrf import anonymous_csrf_exempt

from webpay.base.decorators import json_view
from utils import set_user

log = commonware.log.getLogger('w.auth')


@anonymous_csrf_exempt
@require_POST
@json_view
def verify(request):
    form = BrowserIDForm(data=request.POST)
    if form.is_valid():
        log.info('verifying assertion')
        result = verify_assertion(form.cleaned_data['assertion'],
                                  get_audience(request))
        if result:
            log.info('assertion ok: %s' % result)
            set_user(request, result['email'])
            return {'has_pin': request.session['uuid_has_pin'],
                    'pin_create': reverse('pin.create')}

    request.session.clear()
    return http.HttpResponseBadRequest()


def logout(request):
    # do logout stuff
    return
