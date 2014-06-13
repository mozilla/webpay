from django import http

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import (HttpResponseForbidden, HttpResponseNotFound)
from django.shortcuts import render

from django_paranoia.decorators import require_GET

from lib.solitude.api import ProviderHelper
from webpay.base.logger import getLogger

log = getLogger('w.spa')


@require_GET
def index(request):
    """Page that serves the static Single Page App (Spartacus)."""

    if not settings.ENABLE_SPA:
        return http.HttpResponseForbidden()

    return render(request, 'spa/index.html')


@require_GET
def wait_to_finish(request, provider_name):
    """After the payment provider finishes the pay flow, wait for completion.

    The provider redirects here so the UI can poll Solitude until the
    transaction is complete.

    This view loads up the spa on a specific URL.

    """
    if not settings.ENABLE_SPA:
        return http.HttpResponseForbidden()

    helper = ProviderHelper(provider_name)
    trans_uuid = helper.provider.transaction_from_notice(request.GET)
    if not trans_uuid:
        # This could happen if someone is tampering with the URL or if
        # the payment provider changed their URL parameters.
        log.info('no transaction found for provider {p}; url: {u}'
                 .format(p=helper.provider.name, u=request.get_full_path()))
        return HttpResponseNotFound()

    trans_url = reverse('provider.transaction_status', args=[trans_uuid])

    # For the SPA we are serving up the app on the wait-to-finish url.
    return render(request, 'spa/index.html',
                  {'transaction_status_url': trans_url})
