import functools

import commonware.log

from django.core.exceptions import PermissionDenied

log = commonware.log.getLogger('w.auth')


def user_verified(f):
    @functools.wraps(f)
    def wrapper(request, *args, **kw):
        if not request.session.get('uuid'):
            log.error('No uuid in session, not verified.')
            raise PermissionDenied
        return f(request, *args, **kw)
    return wrapper
