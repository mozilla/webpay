import time

from django import http
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.http import require_GET, require_POST

from django_statsd.clients import statsd
from rest_framework import response, serializers, viewsets

from lib.solitude import constants
from lib.solitude.api import client, ProviderHelper
from lib.solitude.constants import PROVIDERS_INVERTED
from webpay.api.base import BuyerIsLoggedIn
from webpay.base import dev_messages as msg
from webpay.base.logger import getLogger
from webpay.base.utils import system_error
from webpay.auth.decorators import user_verified
from webpay.base.decorators import json_view

from . import tasks
from .views import configure_transaction, process_pay_req

log = getLogger('w.pay')


class TransactionSerializer(serializers.Serializer):
    provider = serializers.CharField()
    pay_url = serializers.CharField()

    def __init__(self, data):
        if 'provider' in data and data['provider'] in PROVIDERS_INVERTED:
            data['provider'] = PROVIDERS_INVERTED[data['provider']]
        super(TransactionSerializer, self).__init__(data)


class PayViewSet(viewsets.ViewSet):
    permission_classes = (BuyerIsLoggedIn,)

    def create(self, request):
        res = process_pay_req(request, data=request.DATA)
        if isinstance(res, http.HttpResponse):
            return res
        return configure_transaction(request, data=request.DATA)

    def retrieve(self, request):
        try:
            trans_id = request.session['trans_id']
            transaction = client.get_transaction(uuid=trans_id)
        except ObjectDoesNotExist:
            return response.Response({
                'error_code': 'TRANSACTION_NOT_FOUND',
                'error': 'Transaction could not be found.',
            }, status=404)
        except KeyError:
            return response.Response({
                'error_code': 'TRANS_ID_NOT_SET',
                'error': 'trans_id was not set.',
            }, status=400)
        else:
            serializer = TransactionSerializer(transaction)
            return response.Response(serializer.data)


@user_verified
@json_view
@require_GET
def trans_start_url(request):
    """
    JSON handler to get the provider payment URL to start a transaction.
    """
    trans = None
    trans_id = request.session.get('trans_id')
    data = {'url': None, 'status': None, 'provider': None}

    if not trans_id:
        log.error('trans_start_url(): no transaction ID in session')
        return http.HttpResponseBadRequest()
    try:
        statsd.incr('purchase.payment_time.retry')
        with statsd.timer('purchase.payment_time.get_transaction'):
            trans = client.get_transaction(trans_id)
        data['status'] = trans['status']
        data['provider'] = constants.PROVIDERS_INVERTED.get(trans['provider'])
    except ObjectDoesNotExist:
        log.error('trans_start_url() transaction does not exist: {t}'
                  .format(t=trans_id))

    if data['status'] == constants.STATUS_PENDING:
        statsd.incr('purchase.payment_time.success')
        payment_start = request.session.get('payment_start', False)
        if payment_start:
            delta = int((time.time() - float(payment_start)) * 1000)
            statsd.timing('purchase.payment_time.duration', delta)
        url = get_payment_url(trans)
        log.info('async call got payment URL {url} for trans {tr}'
                 .format(url=url, tr=trans))
        data['url'] = url

    if trans and trans['status'] == constants.STATUS_ERRORED:
        statsd.incr('purchase.payment_time.errored')
        log.exception('Purchase configuration failed: {0} with status {1}'
                      .format(trans_id, trans['status']))
        return system_error(
            request,
            code=getattr(msg, trans.get('status_reason', 'UNEXPECTED_ERROR'))
        )

    return data


def get_payment_url(transaction):
    """
    Given a Solitude transaction object, return a URL to start the payment
    flow for this provider.
    """
    # A transaction pay_url is configured at the time that a
    # transaction is started.
    url = transaction['pay_url']
    log.info('Start pay provider payflow "{pr}" for '
             'transaction {tr} at: {url}'
             .format(pr=transaction.get('provider'), url=url,
                     tr=transaction.get('uuid')))
    return url


def _callback_url(request, is_success):
    status = is_success and 'success' or 'error'
    signed_notice = request.POST['signed_notice']
    statsd.incr('purchase.payment_{0}_callback.received'.format(status))

    # This is currently only used by Bango and Zippy.
    # Future providers should probably get added to the notification
    # abstraction in provider/views.py
    provider = ProviderHelper(settings.PAYMENT_PROVIDER)

    if provider.is_callback_token_valid(signed_notice):
        statsd.incr('purchase.payment_{0}_callback.ok'.format(status))
        log.info('Callback {0} token was valid.'.format(status))
        querystring = http.QueryDict(signed_notice)
        if 'ext_transaction_id' in querystring:
            ext_transaction_id = querystring['ext_transaction_id']
            if is_success:
                tasks.payment_notify.delay(ext_transaction_id)
            else:
                tasks.chargeback_notify.delay(ext_transaction_id)
            return http.HttpResponse(status=204)
        else:
            statsd.incr('purchase.payment_{0}_callback.incomplete'
                        ''.format(status))
            log.error('Callback {0} token was incomplete: '
                      '{1}'.format(status, querystring))
    else:
        statsd.incr('purchase.payment_{0}_callback.fail'.format(status))
        log.error('Callback {0} token was invalid: '
                  '{1}'.format(status, signed_notice))
    return http.HttpResponseBadRequest()


@require_POST
def callback_success_url(request):
    """
    Hit by the provider to confirm a success of a transaction
    in case of an interruption in the payment process.
    """
    return _callback_url(request, is_success=True)


@require_POST
def callback_error_url(request):
    """
    Hit by the provider to confirm a failure of a transaction
    in case of an interruption in the payment process.
    """
    return _callback_url(request, is_success=False)
