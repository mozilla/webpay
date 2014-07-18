from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from rest_framework import permissions, response, serializers, viewsets

from lib.solitude.api import client
from lib.solitude.constants import PROVIDERS_INVERTED

from webpay.auth.utils import set_user_has_pin
from webpay.base.utils import app_error
from webpay.pay.views import process_pay_req, configure_transaction
from webpay.pin.forms import CreatePinForm, ResetPinForm, VerifyPinForm


class Permission(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        return bool(request.session.get('uuid'))


class PinSerializer(serializers.Serializer):
    pin = serializers.BooleanField(default=False)
    pin_locked_out = serializers.DateTimeField()
    pin_is_locked_out = serializers.BooleanField(default=False)
    pin_was_locked_out = serializers.BooleanField(default=False)
    pin_reset_started = serializers.BooleanField(default=False)


class TransactionSerializer(serializers.Serializer):
    provider = serializers.CharField()
    pay_url = serializers.CharField()

    def __init__(self, data):
        if 'provider' in data and data['provider'] in PROVIDERS_INVERTED:
            data['provider'] = PROVIDERS_INVERTED[data['provider']]
        super(TransactionSerializer, self).__init__(data)


class PinViewSet(viewsets.ViewSet):
    permission_classes = (Permission,)
    serializer_class = PinSerializer

    def retrieve(self, request):
        res = client.get_buyer(request.session['uuid'])
        if res:
            res['pin_reset_started'] = request.session.get(
                'was_reverified', False)
        serial = PinSerializer(res or None)
        return response.Response(serial.data)

    def create(self, request):
        form = CreatePinForm(uuid=request.session['uuid'], data=request.DATA)
        if form.is_valid():
            res = client.change_pin(form.uuid,
                                    form.cleaned_data['pin'],
                                    etag=form.buyer_etag,
                                    pin_confirmed=True,
                                    clear_was_locked=True)

            if form.handle_client_errors(res):
                set_user_has_pin(request, True)

            return response.Response(status=204)

        return app_error(request)

    def update(self, request):
        form = ResetPinForm(uuid=request.session['uuid'], data=request.DATA)

        if not request.session.get('was_reverified', False):
            return app_error(request)

        if form.is_valid():
            res = client.change_pin(form.uuid,
                                    form.cleaned_data['pin'],
                                    pin_confirmed=True,
                                    clear_was_locked=True)
            if form.handle_client_errors(res):
                request.session['was_reverified'] = False
                return response.Response(status=204)

        return app_error(request)


class PinCheckViewSet(viewsets.ViewSet):
    permission_classes = (Permission,)
    serializer_class = PinSerializer

    def check(self, request):
        form = VerifyPinForm(uuid=request.session['uuid'], data=request.DATA)
        try:
            status = 200 if form.is_valid() else 400
        except ObjectDoesNotExist:
            raise Http404
        res = client.get_buyer(request.session['uuid'])
        serial = PinSerializer(res)
        return response.Response(serial.data, status=status)


class PayViewSet(viewsets.ViewSet):
    permission_classes = (Permission,)

    def create(self, request):
        res = process_pay_req(request, request.DATA)
        if res:
            return res
        res = configure_transaction(request)
        if res.status_code == 200:
            return response.Response(status=204)
        else:
            return res

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
