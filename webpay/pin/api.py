from django.http import Http404
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import response, serializers, viewsets

from lib.solitude.api import client
from webpay.api.base import BuyerIsLoggedIn
from webpay.api.utils import api_error
from webpay.auth.utils import set_user_has_pin
from webpay.pin.forms import CreatePinForm, ResetPinForm, VerifyPinForm


class PinSerializer(serializers.Serializer):
    pin = serializers.BooleanField(default=False)
    pin_locked_out = serializers.DateTimeField()
    pin_is_locked_out = serializers.BooleanField(default=False)
    pin_was_locked_out = serializers.BooleanField(default=False)


class PinViewSet(viewsets.ViewSet):
    permission_classes = (BuyerIsLoggedIn,)
    serializer_class = PinSerializer

    def retrieve(self, request):
        res = client.get_buyer(request.session['uuid'])
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

            if form.client_response_is_valid(res):
                set_user_has_pin(request, True)
                return response.Response(status=204)

        return api_error(form, request)

    def update(self, request):
        form = ResetPinForm(uuid=request.session['uuid'], data=request.DATA,
                            user_reset=request.session.get('user_reset', {}))
        if form.is_valid():
            del request.session['user_reset']
            res = client.change_pin(form.uuid,
                                    form.cleaned_data['pin'],
                                    pin_confirmed=True,
                                    clear_was_locked=True)
            if form.client_response_is_valid(res):
                return response.Response(status=204)

        return api_error(form, request)


class PinCheckViewSet(viewsets.ViewSet):
    permission_classes = (BuyerIsLoggedIn,)
    serializer_class = PinSerializer

    def check(self, request):
        form = VerifyPinForm(uuid=request.session['uuid'], data=request.DATA)
        try:
            if form.is_valid():
                status = 200
            else:
                status = 400
        except ObjectDoesNotExist:
            raise Http404
        res = client.get_buyer(request.session['uuid'])
        serial = PinSerializer(res)
        return response.Response(serial.data, status=status)
