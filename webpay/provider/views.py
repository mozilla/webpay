from django.conf import settings
from django.shortcuts import render

from django_paranoia.decorators import require_GET

from webpay.base import dev_messages as msg
from webpay.base.logger import getLogger
from webpay.base.utils import system_error
from webpay.pay import tasks

log = getLogger('w.provider')
NoticeClasses = {}
PREPARED_OK = 'PREPARED_OK'


@require_GET
def success(request, provider):
    if provider != 'reference':
        raise NotImplementedError(
                'only the reference provider is implemented so far')

    notice = NoticeClasses[provider](request.GET)
    result = _prepare_notice(notice, request)
    if result is not PREPARED_OK:
        return system_error(request, code=result)

    tasks.payment_notify.delay(notice.transaction_id)
    return render(request, 'provider/success.html')


@require_GET
def error(request, provider):
    raise NotImplementedError


def register(provider):
    """
    Register a Notice class for provider.
    """
    if provider not in settings.PAYMENT_PROVIDERS:
        raise ValueError('provider {pr} is not recognized'
                         .format(pr=provider))

    def register_cls(cls):
        cls.provider = provider
        NoticeClasses[provider] = cls
        return cls

    return register_cls


class Notice(object):
    """
    Abstract class for parsing query string notices from a provider.
    """
    provider = None  # set by @register_cls

    def __init__(self, query_string):
        self.qs = query_string

    @property
    def transaction_id(self):
        """
        Returns the transaction ID from the notice.
        """
        raise NotImplementedError

    @property
    def token(self):
        """
        Returns the notice token for verification.
        """
        raise NotImplementedError


@register('reference')
class RefNotice(Notice):

    @property
    def transaction_id(self):
        return self.qs.get('ext_transaction_id')


def _prepare_notice(notice, request):
    trans_id = notice.transaction_id
    session_trans_id = request.session.get('trans_id')

    if not trans_id:
        log.info('Provider={pr} did not provide a transaction ID on the query '
                 'string'.format(pr=notice.provider))
        return msg.NO_ACTIVE_TRANS
    if trans_id != session_trans_id:
        log.info('Provider={pr} transaction {tr} is not in the '
                 'active session'.format(pr=notice.provider, tr=trans_id))
        return msg.NO_ACTIVE_TRANS

    # TODO: verify notice.token. bug 936138

    return PREPARED_OK
