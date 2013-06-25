import base64

from webpay.base.logger import getLogger

log = getLogger('w.bango')


def basic(request):
    header = request.META.get('HTTP_AUTHORIZATION', '')
    if not header:
        log.info('No Authorization header')
        raise ValueError

    try:
        auth_type, data = header.split()
    except ValueError:
        log.info("Invalid header, can't split")
        raise ValueError

    if auth_type.lower() != 'basic':
        log.info('Authorization type {0} not supported'.format(auth_type))
        raise ValueError

    # This doesn't actually do the auth. It just splits out the values. It
    # will be solitude's job to actually check these values.
    try:
        return base64.b64decode(data).split(':')
    except TypeError:
        log.info("Invalid header, can't decode")
        raise ValueError
