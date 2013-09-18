import functools

from django.conf import settings
from django.shortcuts import render

from cef import log_cef as _log_cef
from tower import ugettext as _

from webpay.base.logger import getLogger

log = getLogger('w.pay')


def log_cef(msg, request, **kw):
    log_cef_meta(msg, request.META.copy(), request.get_full_path(), **kw)


def log_cef_meta(msg, meta, full_path, **kw):
    g = functools.partial(getattr, settings)
    severity = kw.get('severity', g('CEF_DEFAULT_SEVERITY', 5))
    cef_kw = {
        'msg': msg,
        'signature': full_path,
        'config': {
            'cef.product': 'WebPay',
            'cef.vendor': g('CEF_VENDOR', 'Mozilla'),
            'cef.version': g('CEF_VERSION', '0'),
            'cef.device_version': g('CEF_DEVICE_VERSION', '0'),
            'cef.file': g('CEF_FILE', 'syslog'),
        },
    }
    _log_cef(msg, severity, meta, **cef_kw)


def app_error(request, **kw):
    user_message = _('There was an error setting up the payment. '
                     'Try again or contact the app if it persists.')
    return custom_error(request, user_message, **kw)


def system_error(request, **kw):
    user_message = _('There was an internal error processing the '
                     'payment. Try again or contact Mozilla if it '
                     'persists.')
    return custom_error(request, user_message, **kw)


def custom_error(request, user_message, code=None, status=400):
    return render(request, 'error.html',
                  {'error': user_message, 'error_code': code}, status=status)
