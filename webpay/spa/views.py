import urlparse
from django import http
from django.conf import settings
from django.shortcuts import render

from django_paranoia.decorators import require_GET
from mozpay.verify import InvalidJWT, _get_issuer, verify_sig
from webpay.auth.utils import set_user
from webpay.base.helpers import fxa_auth_info
from webpay.base.logger import getLogger
log = getLogger('w.spa')


@require_GET
def index(request, view_name=None):
    """Page that serves the static Single Page App (Spartacus)."""
    if not settings.SPA_ENABLE:
        return http.HttpResponseForbidden()
    ctx = {'mkt_user': False}
    ctx['fxa_state'], ctx['fxa_auth_url'] = fxa_auth_info(request)
    jwt = request.GET.get('req')
    # If this is a Marketplace-issued JWT, verify its signature and skip login
    # for the purchaser named in it.
    if jwt and _get_issuer(jwt) == settings.KEY:
        try:
            data = verify_sig(jwt, settings.SECRET)
            data = data['request'].get('productData', '')
        except InvalidJWT:
            pass
        else:
            product_data = urlparse.parse_qs(data)
            emails = product_data.get('buyer_email')
            if emails:
                log.info("Creating session for marketplace user " +
                         str(emails))
                set_user(request, emails[0], verified=False)
                ctx['mkt_user'] = True
    return render(request, 'spa/index.html', ctx)
