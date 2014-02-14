from django.http import Http404

from lib.solitude.api import client

from rest_framework import permissions, response, serializers, viewsets

from webpay.auth.utils import set_user_has_pin
from webpay.base.utils import app_error
from webpay.pay.views import process_pay_req
from webpay.pin.forms import CreatePinForm, ResetPinForm


class Permission(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        return bool(request.session.get('uuid'))


class PinSerializer(serializers.Serializer):
    pin = serializers.BooleanField()
    pin_locked_out = serializers.DateTimeField()
    pin_is_locked_out = serializers.BooleanField()
    pin_was_locked_out = serializers.BooleanField()


class Flag(object):

    def dispatch(self, request, *args, **kwargs):
        return super(Flag, self).dispatch(request, *args, **kwargs)


class PinViewSet(Flag, viewsets.ViewSet):
    permission_classes = (Permission,)
    serializer_class = PinSerializer

    def retrieve(self, request):
        res = client.get_buyer(request.session['uuid'])
        if not res:
            raise Http404
        serial = PinSerializer(res)
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
                return response.Response(status=201)

            return response.Response(status=201)

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


class PayViewSet(Flag, viewsets.ViewSet):
    permission_classes = (Permission,)

    def create(self, request):
        res = process_pay_req(request, request.DATA)
        if res:
            return res

        return response.Response(status=204)
