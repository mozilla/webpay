from django import http
from django.views.decorators.http import require_POST

import commonware.log
from django_browserid import get_audience, verify as verify_assertion
from django_browserid.forms import BrowserIDForm
from session_csrf import anonymous_csrf_exempt

log = commonware.log.getLogger('w.pay')


@anonymous_csrf_exempt
@require_POST
def verify(request):
    form = BrowserIDForm(data=request.POST)
    if form.is_valid():
        log.info('verifying assertion')
        result = verify_assertion(form.cleaned_data['assertion'],
                                  get_audience(request))
        if result:
            log.info('assertion ok: %s' % result)
            return http.HttpResponse('ok')

    return http.HttpResponseBadRequest()
