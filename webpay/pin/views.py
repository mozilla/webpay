from django.shortcuts import render

from session_csrf import anonymous_csrf_exempt

from lib.solitude.api import client
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
                client.change_pin(form.buyer, form.cleaned_data['pin'])
            else:
                client.create_buyer(form.uuid, form.cleaned_data['pin'])
            # TODO(Wraithan): Replace with proper redirect
            return render(request, 'pin/create_success.html', {'form': form})
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
            # TODO(Wraithan): Replace with proper redirect
            return render(request, 'pin/verify_success.html', {'form': form})
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
            client.change_pin(stub_uuid, form.cleaned_data['new_pin'])
            # TODO(Wraithan): Replace with proper redirect
            return render(request, 'pin/change_success.html', {'form': form})
    return render(request, 'pin/change.html', {'form': form})
