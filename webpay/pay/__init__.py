import time

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.conf import settings

from webpay.auth.decorators import user_can_simulate
from webpay.base.logger import getLogger

log = getLogger('w.pay')


def get_payment_url(request):
    """
    After all authentication, get the URL to start the payment flow.
    """
    try:
        # Re-use the view decorator.
        user_can_simulate(lambda r: None)(request)
        can_simulate = True
    except PermissionDenied:
        can_simulate = False

    if can_simulate:
        return reverse('pay.super_simulate')
    else:
        request.session['payment_start'] = time.time()
        return reverse('pay.wait_to_start')
