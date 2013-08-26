import json

from django import http
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from curling.lib import HttpClientError

from lib.marketplace.api import client as marketplace
from lib.solitude.api import client as solitude

from .forms import SigCheckForm


def monitor(request):
    content = {}
    all_good = True

    # Check that we can talk to the marketplace.
    msg = 'ok'
    try:
        perms = marketplace.api.account.permissions.mine.get()
    except HttpClientError, err:
        all_good = False
        msg = ('Server error: status %s, content: %s' %
               (err.response.status_code, err.response.content or 'empty'))
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
