from django import http
from django.conf import settings
from django.shortcuts import render

from webpay.base.logger import getLogger

log = getLogger('w.pay')


def index(request):
    """Page that serves the static Single Page App (Spartacus)."""

    if not settings.ENABLE_SPA:
        return http.HttpResponseForbidden()

    return render(request, 'spa/index.html')
