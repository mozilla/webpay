import base64

from django.conf import settings

import commonware.log

log = commonware.log.getLogger('w.bango')


def basic(request):
    header = request.META.get('HTTP_AUTHORIZATION', '')
    if not header:
        log.info('No Authorization header')
        return False

    try:
        auth_type, data = header.split()
    except ValueError:
        log.info("Invalid header, can't split")
        return False

    if auth_type.lower() != 'basic':
        log.info('Authorization type {0} not supported'.format(auth_type))
        return False

    try:
        user, passwd = base64.b64decode(data).split(':')
    except TypeError:
        log.info("Invalid header, can't decode")
        return False

    if (user != settings.BANGO_BASIC_AUTH['user'] or
        passwd != settings.BANGO_BASIC_AUTH['password']):
        log.info('User name and password did not match')
        return False

    log.info('Bango Basic Authentication successful')
    return True
