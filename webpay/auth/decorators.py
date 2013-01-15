import functools

import commonware.log

from django import http
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse

from utils import log_cef


log = commonware.log.getLogger('w.auth')

flow = {
    'standard': ['create', 'confirm', 'verify', 'reset_start'],
    'reset': ['reset_new_pin', 'reset_confirm', 'reset_cancel'],
}

def log_redirect(request, step, dest):
    log_cef('Buyer was attempting %s redirecting to: %s' % (step, dest),
            request)

def user_verified(f):
    @functools.wraps(f)
    def wrapper(request, *args, **kw):
        if not request.session.get('uuid'):
            log_cef('No UUID in session, not verified', request)
            raise PermissionDenied
        return f(request, *args, **kw)
    return wrapper


def enforce_sequence(func):
    def wrapper(request, *args, **kw):
        step = func.func_name
        if not request.session.get('uuid'):
            log_cef('No UUID in session, not verified', request)
            raise PermissionDenied
        if request.session.get('uuid_needs_pin_reset'):
            return get_reset_step(request, step) or func(request, *args, **kw)
        return get_standard_step(request, step) or func(request, *args, **kw)
    return functools.wraps(func)(wrapper)


def get_reset_step(request, step):
    """Returns the view the buyer should be at or None if they are already
    there. This is only called if they already have needs_pin_reset flag set.

    :rtype: HttpResponse or None
    """
    try:
        step_index = flow['reset'].index(step)
    except ValueError:
        step_index = -1

    # If they have a new pin already, make sure they are headed to confirm or
    # cancel.
    if request.session.get('uuid_has_new_pin'):
        if step_index < flow['reset'].index('reset_confirm'):
            log_redirect(request, step, 'reset_confirm')
            return http.HttpResponseRedirect(reverse('pin.reset_confirm'))

    # If they haven't set their new pin yet, make sure they are headed to do
    # that.
    elif step_index != flow['reset'].index('reset_new_pin'):
        log_redirect(request, step, 'reset_new_pin')
        return http.HttpResponseRedirect(reverse('pin.reset_new_pin'))


def get_standard_step(request, step):
    """Returns the view the buyer should be at or None if they are already
    there.

    :rtype: HttpResponse or None
    """
    try:
        step_index = flow['standard'].index(step)
    except ValueError:
        step_index = -1

    # Check to see if the buyer has confirmed their pin, if they are trying to
    # hit a step that comes before that, redirect them to verify
    if request.session.get('uuid_has_confirmed_pin'):
        # -1 means they are in a different flow
        if step_index < flow['standard'].index('verify') or step_index == -1:
            log_redirect(request, step, 'verify')
            return http.HttpResponseRedirect(reverse('pin.verify'))

    # Buyer hasn't confirmed pin, check that they have a pin, if they are
    # trying to hit a step that isn't confirming their pin, redirect them.
    elif request.session.get('uuid_has_pin'):
        if step_index != flow['standard'].index('confirm'):
            log_redirect(request, step, 'confirm')
            return http.HttpResponseRedirect(reverse('pin.confirm'))

    # Buyer has no pin, send them to create if they aren't already headed
    # there.
    elif step_index > flow['standard'].index('create'):
        log_redirect(request, step, 'create')
        return http.HttpResponseRedirect(reverse('pin.create'))
