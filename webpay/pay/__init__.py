from django.core.urlresolvers import reverse
from django.conf import settings

from webpay.base.logger import getLogger

log = getLogger('w.pay')


def get_payment_url():
    if settings.FAKE_PAYMENTS:
        return reverse('pay.fakepay')
    else:
        return reverse('pay.wait_to_start')
