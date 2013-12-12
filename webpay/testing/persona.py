from os.path import abspath
from time import time, sleep

from django import http
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from webpay.base.decorators import json_view
from webpay.base.logger import getLogger

log = getLogger('w.pay')

# When email addressess are prefixed with these values they will trigger login
# behavior.
OK_USER = 'tester'
TIMEOUT_USER = 'timeout'
FAILED_LOGIN = 'fail'
ERROR_LOGIN = '500'


def fake_include(request):
    """Serve up stubbyid.js for testing."""
    if not settings.DEV or not settings.TEST_PIN_UI:
        return http.HttpResponseForbidden()

    with open(abspath('webpay/testing/stubbyid.js')) as fh:
        stub_js = fh.read()
    return http.HttpResponse(stub_js,
                             content_type='text/javascript')


@csrf_exempt
@json_view
def fake_verify(request):
    """Fake verification for testing"""

    if not settings.DEV or not settings.TEST_PIN_UI:
        return http.HttpResponseForbidden()

    # This is not a real assertion, it's an email address.
    assertion = request.POST.get('assertion')
    success = {
        'status': 'okay',
        'audience': 'http://localhost:9765',
        'expires': int(time()),
        'issuer': 'fake-persona'
    }

    success['email'] = assertion
    log.info('logging in {email}'.format(email=assertion))
    if assertion.startswith(OK_USER):
        log.info('ok')
        return success
    elif assertion.startswith(TIMEOUT_USER):
        sleep(10)
        log.info('ok')
        return success
    elif assertion.startswith(ERROR_LOGIN):
        log.info('fail')
        return http.HttpResponseServerError()
    elif assertion.startswith(FAILED_LOGIN):
        request.session.clear()
        log.info('fail')
        return http.HttpResponseBadRequest()
