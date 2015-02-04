from django import http
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import response, serializers, viewsets

from lib.solitude.api import client
from lib.solitude.constants import PROVIDERS_INVERTED

from webpay.base.logger import getLogger
from webpay.pay.views import configure_transaction, process_pay_req, simulate

from .base import BuyerIsLoggedIn

log = getLogger('w.api')


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


class SimulateViewSet(viewsets.ViewSet):
    permission_classes = (BuyerIsLoggedIn,)

    def create(self, request):
        res = simulate(request)
        if res.status_code == 200:
            res = response.Response(status=204)
        return res
