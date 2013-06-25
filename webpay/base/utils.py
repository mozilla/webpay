import functools

from django.conf import settings
from django.shortcuts import render

from cef import log_cef as _log_cef
from tower import ugettext as _

from webpay.base.logger import getLogger

log = getLogger('w.pay')


def log_cef(msg, request, **kw):
    g = functools.partial(getattr, settings)
    severity = kw.get('severity', g('CEF_DEFAULT_SEVERITY', 5))
    cef_kw = {
        'msg': msg,
        'signature': request.get_full_path(),
        'config': {
            'cef.product': 'WebPay',
            'cef.vendor': g('CEF_VENDOR', 'Mozilla'),
            'cef.version': g('CEF_VERSION', '0'),
            'cef.device_version': g('CEF_DEVICE_VERSION', '0'),
            'cef.file': g('CEF_FILE', 'syslog'),
        },
    }
    _log_cef(msg, severity, request.META.copy(), **cef_kw)


def _error(request, msg='', exception=None, display=False):
    external = _('There was an error processing that request.')
    if msg:
        log.error('Error handler: %s' % msg)
    if settings.VERBOSE_LOGGING or display:
        if exception:
            msg = u'%s: %s' % (exception.__class__.__name__, exception)
        if msg:
            external = msg
        if not exception and not msg:
            # This should never happen but it might be happening.
            # See bug 864306
            log.error('No detailed error message/exception in handler')
    return render(request, 'error.html', {'error': external}, status=400)
