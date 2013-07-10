import functools

from django import http
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse

from webpay.base.logger import getLogger
from webpay.base.utils import log_cef


log = getLogger('w.auth')

flow = {
    'standard': ['create', 'confirm', 'verify', 'reset_start'],
    'locked': ['is_locked', 'was_locked'],
    'reset': ['reset_new_pin', 'reset_confirm', 'reset_cancel'],
}


def log_redirect(request, step, dest):
    msg = 'Buyer was attempting %s redirecting to: %s' % (step, dest)
    log.info('enforce_sequence: %s' % msg)
    log_cef(msg, request)


def user_verified(f):
    @functools.wraps(f)
    def wrapper(request, *args, **kw):
        if not request.session.get('uuid'):
            log_cef('No UUID in session, not verified', request)
            raise PermissionDenied
        return f(request, *args, **kw)
    return wrapper


def enforce_sequence(func):
    def wrapper(request, *args, **kwargs):
        step = func.func_name
        if not request.session.get('uuid'):
            log_cef('No UUID in session, not verified', request)
            raise PermissionDenied

        locked_step = get_locked_step(request, step)
        if locked_step is False:  # Purposefully using is to not match None.
            if request.session.get('uuid_needs_pin_reset'):
                return get_reset_step(request, step) or func(request, *args,
                                                             **kwargs)
            return get_standard_step(request, step) or func(request, *args,
                                                            **kwargs)
        return locked_step or func(request, *args, **kwargs)
    return functools.wraps(func)(wrapper)


def get_reset_step(request, step):
    """Returns the view the buyer should be at or returns None if they are
    already at the right view. This is only called if they already have
    `needs_pin_reset` flag set.

    :rtype: HttpResponse or None
    """
    try:
        step_index = flow['reset'].index(step)
    except ValueError:
        step_index = -1

    # If they have not reverified, send them to start to reverification.
    if not request.session.get('was_reverified'):
        log_redirect(request, step, 'reset_start')
        return http.HttpResponseRedirect(reverse('pin.reset_start'))

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


def get_locked_step(request, step):
    """Returns the locked view the buyer should be at, None if they are
    already there, or False if they don't need the lock views.

    :rtype: HttpResponse or None or False

    """
    try:
        step_index = flow['locked'].index(step)
    except ValueError:
        step_index = -1

    if request.session.get('uuid_pin_is_locked'):
        if step_index != flow['locked'].index('is_locked'):
            log_redirect(request, step, 'is_locked')
            return http.HttpResponseRedirect(reverse('pin.is_locked'))
        return None
    elif request.session.get('uuid_pin_was_locked'):
        if step_index != flow['locked'].index('was_locked'):
            log_redirect(request, step, 'was_locked')
            return http.HttpResponseRedirect(reverse('pin.was_locked'))
        return None
    return False
