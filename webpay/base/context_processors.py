from django.conf import settings
from webpay.pay.constants import PIN_ERROR_CODES

from lib.solitude import constants as solitude_constants
from . import dev_messages


def defaults(request):
    return {'session': request.session,
            'STATIC_URL': settings.STATIC_URL,
            'PIN_ERROR_CODES': PIN_ERROR_CODES,
            'USAGE_WARNING': settings.USAGE_WARNING,
            'dev_messages': dev_messages,
            'solitude_constants': solitude_constants}
