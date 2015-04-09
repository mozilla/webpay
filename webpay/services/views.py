import json

from django import http
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import translation

from curling.lib import HttpClientError, HttpServerError
from rest_framework import viewsets

from lib.marketplace.api import client as marketplace
from lib.solitude.api import client as solitude
from webpay.base.decorators import json_view
from webpay.base.dev_messages import legend
from webpay.base.logger import getLogger
from webpay.base.utils import log_cef_meta

from .forms import ErrorLegendForm, SigCheckForm

log = getLogger('z.services')


def monitor(request):
    content = {}
    all_good = True

    # Check that we can talk to the marketplace.
    msg = 'ok'
    try:
        perms = marketplace.api.account.permissions.mine.get()
    except (HttpServerError, HttpClientError), err:
        all_good = False
        msg = ('Server error: status {0}, content: {1}'.format(
            err.response.status_code,
            err.response.content or 'empty')
            if err.response else 'Server error: no response')
    else:
        if not perms['permissions'].get('webpay', False):
            all_good = False
            msg = 'User does not have webpay permission'

    content['marketplace'] = msg

    # Check that we can talk to solitude.
    msg = 'ok'
    try:
        users = solitude.slumber.services.request.get()
    except HttpClientError, err:
        all_good = False
        msg = ('Server error: status %s, content: %s' %
               (err.response.status_code, err.response.content or 'empty'))
    else:
        if not users['authenticated'] == 'webpay':
            all_good = False
            msg = 'Not the webpay user, got: %s' % users['authenticated']

    content['solitude'] = msg
    return http.HttpResponse(content=json.dumps(content),
                             content_type='application/json',
                             status=200 if all_good else 500)


@require_POST
@csrf_exempt
def sig_check(request):
    form = SigCheckForm(request.POST)
    result = 'ok'
    errors = {}
    if not form.is_valid():
        result = 'error'
        errors = form.errors
    res = {'result': result, 'errors': errors}
    return http.HttpResponse(content=json.dumps(res),
                             content_type='application/json',
                             status=200 if res['result'] == 'ok' else 400)


@csrf_exempt
@require_POST
def csp_report(request):
    """Accept CSP reports and log them."""
    whitelist = ('blocked-uri', 'violated-directive', 'original-policy')

    try:
        report = json.loads(request.raw_post_data)['csp-report']
        # If possible, alter the PATH_INFO to contain the request of the page
        # the error occurred on, spec: http://mzl.la/P82R5y
        meta = request.META.copy()
        meta['PATH_INFO'] = report.get('document-uri', meta['PATH_INFO'])
        incoming = [(k, report[k]) for k in whitelist if k in report]
        log.info('CSP reported for {0}: {1}'
                 .format(meta['PATH_INFO'], incoming))
        log_cef_meta('CSP Violation', meta, request.path_info,
                     cs6=incoming, cs6Label='ContentPolicy')
    except (KeyError, ValueError):
        return http.HttpResponseBadRequest()

    return http.HttpResponse()


@csrf_exempt
@json_view
def error_legend(request):
    data = {'legend': {},
            'errors': None,
            'locale': translation.get_language()}
    form = ErrorLegendForm(request.GET)
    if not form.is_valid():
        data['errors'] = form.errors
        return http.HttpResponse(content=json.dumps(data), status=400)

    data['locale'] = form.cleaned_data['locale'] or data['locale']
    data['legend'] = legend(locale=data['locale'])
    return data


class APIException(viewsets.ViewSet):

    def retrieve(self, request):
        raise RuntimeError('this exception was intentional')
