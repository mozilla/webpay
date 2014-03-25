from django.conf import settings
from django.shortcuts import render

from django_paranoia.decorators import require_GET
from slumber.exceptions import HttpClientError

from lib.solitude.api import client
from webpay.base import dev_messages as msg
from webpay.base.logger import getLogger
from webpay.base.utils import system_error
from webpay.pay import tasks

log = getLogger('w.provider')
NoticeClasses = {}


@require_GET
def success(request, provider):
    if provider != 'reference':
        raise NotImplementedError(
            'only the reference provider is implemented so far')

    notice = NoticeClasses[provider](request)
    try:
        notice.prepare()
    except msg.DevMessage as m:
        return system_error(request, code=m.code)

    tasks.payment_notify.delay(notice.transaction_id)
    return render(request, 'provider/success.html')


@require_GET
def error(request, provider):
    if provider != 'reference':
        raise NotImplementedError(
            'only the reference provider is implemented so far')

    notice = NoticeClasses[provider](request)
    try:
        notice.prepare()
    except msg.DevMessage as m:
        return system_error(request, code=m.code)

    # TODO: handle user cancellation, bug 957774.

    log.error('Fatal payment error for {provider}: {code}; query string: {qs}'
              .format(provider=provider, code=request.GET.get('ResponseCode'),
                      qs=request.GET))
    return system_error(request, code=msg.EXT_ERROR)


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

    def __init__(self, request):
        self.request = request
        self.qs = request.GET
        if request.GET:
            self.raw_qs = request.get_full_path().split('?')[1]
        else:
            self.raw_qs = ''

    @property
    def api(self):
        """
        Access the top level provider API attribute.

        Example: client.slumber.provider.bango
        """
        return getattr(client.slumber.provider, self.provider)

    def prepare(self):
        trans_id = self.transaction_id
        session_trans_id = self.request.session.get('trans_id')

        if not trans_id:
            log.info('Provider={pr} did not provide a transaction ID '
                     'on the query string'.format(pr=self.provider))
            raise msg.DevMessage(msg.TRANS_MISSING)
        if trans_id != session_trans_id:
            log.info('Provider={pr} transaction {tr} is not in the '
                     'active session'.format(pr=self.provider, tr=trans_id))
            raise msg.DevMessage(msg.NO_ACTIVE_TRANS)

        self.verify_signature()

    @property
    def transaction_id(self):
        """
        Returns the transaction ID from the notice.
        """
        raise NotImplementedError

    def verify_signature(self):
        """
        Returns without raising an exception if the signagture
        of the notification is valid.
        """
        raise NotImplementedError


@register('reference')
class RefNotice(Notice):

    @property
    def transaction_id(self):
        return self.qs.get('ext_transaction_id')

    def verify_signature(self):
        try:
            response = self.api.notices.post({'qs': self.raw_qs})
        except HttpClientError, err:
            log.error('post to reference payment notice for transaction '
                      'ID {trans} failed: {err}'
                      .format(trans=self.transaction_id, err=err))
            raise msg.DevMessage(msg.NOTICE_EXCEPTION)

        log.info('reference payment notice check result={result}; '
                 'trans_id={trans}'.format(trans=self.transaction_id,
                                           result=response['result']))

        if response['result'] != 'OK':
            raise msg.DevMessage(msg.NOTICE_ERROR)
