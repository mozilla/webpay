from django import http
from django.shortcuts import render

from session_csrf import anonymous_csrf_exempt

from lib.solitude.api import client
from webpay.pay import get_payment_url
from . import forms


# TODO(Wraithan): remove all the anonymous once identity is figured out.
@anonymous_csrf_exempt
def create(request):
    form = forms.CreatePinForm()
    if request.method == 'POST':
        # TODO(Wraithan): Get the buyer's UUID once identity is figured out
        # with webpay.
        stub_uuid = 'dat:uuid'
        form = forms.CreatePinForm(uuid=stub_uuid, data=request.POST)
        if form.is_valid():
            if hasattr(form, 'buyer'):
                res = client.change_pin(form.buyer, form.cleaned_data['pin'])
            else:
                res = client.create_buyer(form.uuid, form.cleaned_data['pin'])
            if form.handle_client_errors(res):
                # TODO(Wraithan): Replace with proper redirect
                return render(request, 'pin/create_success.html',
                              {'form': form})
    return render(request, 'pin/create.html', {'form': form})


@anonymous_csrf_exempt
def verify(request):
    form = forms.VerifyPinForm()
    if request.method == 'POST':
        # TODO(Wraithan): Get the buyer's UUID once identity is figured out
        # with webpay.
        stub_uuid = 'dat:uuid'
        form = forms.VerifyPinForm(uuid=stub_uuid, data=request.POST)
        if form.is_valid():
            return http.HttpResponseRedirect(get_payment_url())
    return render(request, 'pin/verify.html', {'form': form})


@anonymous_csrf_exempt
def change(request):
    form = forms.ChangePinForm()
    if request.method == 'POST':
        # TODO(Wraithan): Get the buyer's UUID once identity is figured out
        # with webpay.
        stub_uuid = 'dat:uuid'
        form = forms.ChangePinForm(uuid=stub_uuid, data=request.POST)
        if form.is_valid():
            res = client.change_pin(form.buyer, form.cleaned_data['pin'])
            if form.handle_client_errors(res):
                # TODO(Wraithan): Replace with proper redirect
                return render(request, 'pin/change_success.html',
                              {'form': form})
    return render(request, 'pin/change.html', {'form': form})
