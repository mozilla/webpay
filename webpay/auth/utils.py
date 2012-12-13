import hashlib

from django.conf import settings

from lib.solitude.api import client


def get_uuid(email):
    """
    Given an email returns the hash of the email for this site. This will be
    consistent for each email for this site and can be used as the uuid in
    solitude. Because the leakage of the email is more of a privacy concern
    than a security concern, we are just doing a simple sha1 hash.

    :email: the email to hash.
    """
    if not isinstance(email, basestring):
        raise ValueError('get_uuid requires a string or unicode')
    hashed = hashlib.sha1()
    hashed.update(email)
    return '%s:%s' % (settings.DOMAIN, hashed.hexdigest())


def get_user(request):
    try:
        return request.session.get('uuid')
    except KeyError:
        raise KeyError('Attempt to access user without it being set, '
                       'did you use the user_verified decorator?')


def set_user(request, email):
    uuid = get_uuid(email)
    request.session['uuid'] = uuid
    set_user_has_pin(request, client.buyer_has_pin(uuid))


def set_user_has_pin(request, has_pin):
    request.session['uuid_has_pin'] = has_pin
