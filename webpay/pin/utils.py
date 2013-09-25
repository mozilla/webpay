from datetime import datetime

from django.conf import settings
from django.core.urlresolvers import reverse

from lib.solitude.exceptions import ResourceModified
from webpay.base import dev_messages as msg
from webpay.base.utils import system_error
from webpay.pay import get_payment_url

from lib.solitude.api import client


def check_pin_status(request):
    if request.session.get('uuid_pin_is_locked'):
        return reverse('pin.is_locked')

    if request.session.get('uuid_pin_was_locked'):
        return reverse('pin.was_locked')

    last_success = request.session.get('last_pin_success')
    if (last_success and ((datetime.now() - last_success).seconds <
                          settings.PIN_UNLOCK_LENGTH)):
        return get_payment_url(request)

    if request.session.get('uuid_has_pin'):
        if request.session.get('uuid_has_confirmed_pin'):
            return None
        else:
            try:
                client.change_pin(request.session['uuid'], None)
            except ResourceModified:
                return system_error(request, code=msg.RESOURCE_MODIFIED)
            request.session['uuid_has_pin'] = False
    return reverse('pin.create')
