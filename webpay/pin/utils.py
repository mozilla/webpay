from datetime import datetime

from django.conf import settings


def pin_recently_entered(request):
    last_success = request.session.get('last_pin_success')
    return (last_success and ((datetime.now() - last_success).seconds <
                              settings.PIN_UNLOCK_LENGTH))
