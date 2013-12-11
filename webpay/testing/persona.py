from os.path import abspath
from time import time, sleep

from django import http
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from webpay.base.decorators import json_view

OK_USER = 'tester@fakepersona.mozilla.org'
TIMEOUT_USER = 'timeout@fakepersona.mozilla.org'
FAILED_LOGIN = 'fail@fakepersona.mozilla.org'
ERROR_LOGIN = '500@fakepersona.mozilla.org'


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

    assertion = request.POST.get('assertion')
    success = {
        'status': 'okay',
        'audience': 'http://localhost:9765',
        'expires': int(time()),
        'issuer': 'fake-persona'
    }

    if assertion == OK_USER:
        success['email'] = OK_USER
        return success
    elif assertion == TIMEOUT_USER:
        sleep(10)
        success['email'] = TIMEOUT_USER
        return success
    elif assertion == ERROR_LOGIN:
        return http.HttpResponseServerError()
    elif assertion == FAILED_LOGIN:
        request.session.clear()
        return http.HttpResponseBadRequest()
