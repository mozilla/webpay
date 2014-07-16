from django import http
from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import render

from django_paranoia.decorators import require_GET

from lib.solitude.api import ProviderHelper
from webpay.base.logger import getLogger

log = getLogger('w.spa')


@require_GET
def index(request, view_name=None):
    """Page that serves the static Single Page App (Spartacus)."""

    if not settings.SPA_ENABLE:
        return http.HttpResponseForbidden()

    return render(request, 'spa/index.html')
