import json

from django import http

from curling.lib import HttpClientError

from lib.marketplace.api import client


def monitor(request):
    content = {}
    all_good = True

    # Check that we can talk to the marketplace.
    msg = 'ok'
    try:
        perms = client.api.account.permissions.mine.get()
    except HttpClientError, err:
        all_good = False
        msg = ('Server error: status %s, content: %s' %
               (err.response.status_code, err.response.content or 'empty'))
    else:
        if not perms['permissions'].get('webpay', False):
            all_good = False
            msg = 'User does not have webpay permission'

    content['marketplace'] = msg

    # TODO: lets do the same with solitude.
    return http.HttpResponse(content=json.dumps(content),
                             content_type='application/json',
                             status=200 if all_good else 500)
