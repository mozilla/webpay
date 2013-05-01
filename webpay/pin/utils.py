from datetime import datetime

from django.conf import settings

from lib.solitude.api import client


def pin_recently_entered(request):
    last_success = request.session.get('last_pin_success')
    return (last_success and ((datetime.now() - last_success).seconds <
                              settings.PIN_UNLOCK_LENGTH))


def has_pin(request):
    pin = request.session.get('uuid_has_pin')
    confirmed = request.session.get('uuid_has_confirmed_pin')
    if pin:
        if confirmed:
            return True
        else:
            client.change_pin(request.session['uuid'], None)
            request.session['uuid_has_pin'] = False
    return False
