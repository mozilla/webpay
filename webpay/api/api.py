from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from rest_framework import permissions, response, serializers, viewsets

from lib.solitude.api import client

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


class PinViewSet(viewsets.ViewSet):
    permission_classes = (Permission,)
    serializer_class = PinSerializer

    def retrieve(self, request):
        res = client.get_buyer(request.session['uuid'])
        serial = PinSerializer(res or None)
        return response.Response(serial.data)

    def create(self, request):
        form = CreatePinForm(uuid=request.session['uuid'], data=request.DATA)
        if form.is_valid():
            if getattr(form, 'buyer_exists', None):
                res = client.change_pin(form.uuid,
                                        form.cleaned_data['pin'],
                                        etag=form.buyer_etag)
            else:
                res = client.create_buyer(form.uuid, form.cleaned_data['pin'])

            if form.handle_client_errors(res):
                set_user_has_pin(request, True)

            return response.Response(status=204)

        return app_error(request)

    def update(self, request):
        form = ResetPinForm(uuid=request.session['uuid'], data=request.DATA)

        if not request.session.get('was_reverified', False):
            return app_error(request)

        if form.is_valid():
            res = client.set_new_pin(form.uuid, form.cleaned_data['pin'])
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
