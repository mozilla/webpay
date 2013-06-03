import hashlib
import hmac

from django.conf import settings

from lib.solitude.api import client


def get_uuid(email):
    """
    Given an email returns an email token for this site. This will be
    consistent for each email for this site and can be used as the uuid in
    solitude. The email is protected by HMAC for privacy purposes.

    :email: the email to tokenize.
    """
    if not settings.DEBUG and not settings.UUID_HMAC_KEY:
        raise EnvironmentError('UUID_HMAC_KEY setting cannot be empty in '
                               'production')
    if not isinstance(email, basestring):
        raise ValueError('get_uuid requires a string or unicode')
    if isinstance(email, unicode):
        # Emails should always be UTF8 compatible but let's cope
        # with it if not.
        email = email.encode('utf8', 'replace')
    uid = hmac.new(settings.UUID_HMAC_KEY, email, hashlib.sha256).hexdigest()
    return '%s:%s' % (settings.DOMAIN, uid)


def get_user(request):
    try:
        return request.session.get('uuid')
    except KeyError:
        raise KeyError('Attempt to access user without it being set, '
                       'did you use the user_verified decorator?')


def set_user(request, email):
    uuid = get_uuid(email)
    request.session['uuid'] = uuid
    # This is only used by navigator.id.watch()
    request.session['logged_in_user'] = email
    return update_session(request, uuid)


def update_session(request, uuid):
    buyer = client.get_buyer(uuid)
    set_user_has_pin(request, buyer.get('pin', False))
    set_user_has_confirmed_pin(request, buyer.get('pin_confirmed', False))
    set_user_reset_pin(request, buyer.get('needs_pin_reset', False))
    set_user_has_new_pin(request, buyer.get('new_pin', False))
    request.session['uuid_pin_was_locked'] = buyer.get('pin_was_locked_out',
                                                       False)
    request.session['uuid_pin_is_locked'] = buyer.get('pin_is_locked_out',
                                                      False)
    return uuid


def set_user_has_pin(request, has_pin):
    request.session['uuid_has_pin'] = has_pin


def set_user_has_confirmed_pin(request, has_confirmed_pin):
    request.session['uuid_has_confirmed_pin'] = has_confirmed_pin


def set_user_reset_pin(request, reset_pin):
    request.session['uuid_needs_pin_reset'] = reset_pin


def set_user_has_new_pin(request, has_new_pin):
    request.session['uuid_has_new_pin'] = has_new_pin
