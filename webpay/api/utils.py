from tower import ugettext as _

from webpay.base.logger import getLogger
from webpay.base.utils import custom_error

log = getLogger('w.api')


def api_error(form, request, **kw):
    user_message = _('There was an internal error processing your '
                     'request. Try again or contact Mozilla if it '
                     'persists.')
    if form.errors:
        codes = getattr(form, 'pin_error_codes', [])
        if len(codes):
            log.info('API form error codes: {e}'.format(e=codes))
            # The UI only supports showing one error code at a time now so
            # let's pop them off until the request has no more errors.
            kw['code'] = codes.pop(0)
    return custom_error(request, user_message, **kw)
