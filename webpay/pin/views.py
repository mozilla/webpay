from datetime import datetime

from django import http
from django.core.urlresolvers import reverse
from django.shortcuts import render

import commonware.log

from lib.solitude.api import client
from webpay.auth.decorators import user_verified
from webpay.auth.utils import get_user, set_user_has_pin
from webpay.pay import get_payment_url
from . import forms
from . import utils

log = commonware.log.getLogger('w.pin')


@user_verified
def create(request):
    form = forms.CreatePinForm()
    if request.method == 'POST':
        form = forms.CreatePinForm(uuid=get_user(request), data=request.POST)
        if form.is_valid():
            if hasattr(form, 'buyer'):
                res = client.change_pin(form.buyer, form.cleaned_data['pin'])
            else:
                res = client.create_buyer(form.uuid, form.cleaned_data['pin'])
            if form.handle_client_errors(res):
                set_user_has_pin(request, True)
                return http.HttpResponseRedirect(reverse('pin.confirm'))
    return render(request, 'pin/create.html', {'form': form})


@user_verified
def confirm(request):
    form = forms.ConfirmPinForm()
    if request.method == 'POST':
        form = forms.ConfirmPinForm(uuid=get_user(request), data=request.POST)
        if form.is_valid():
            return http.HttpResponseRedirect(get_payment_url())
    return render(request, 'pin/confirm.html', {'form': form})


@user_verified
def verify(request):
    form = forms.VerifyPinForm()
    # pin_recently_entered is on the form because the template expect it as it
    # is rendered from pay.lobby as well as here.
    form.pin_recently_entered = utils.pin_recently_entered(request)
    if form.pin_recently_entered:
        return http.HttpResponseRedirect(get_payment_url())

    if request.method == 'POST':
        form = forms.VerifyPinForm(uuid=get_user(request), data=request.POST)
        if form.is_valid():
            request.session['last_pin_success'] = datetime.now()
            return http.HttpResponseRedirect(get_payment_url())
        form.pin_recently_entered = False
    return render(request, 'pin/verify.html', {'form': form})


@user_verified
def reset_start(request):
    # TODO(Wraithan): Create dialog to make sure you meant to reset your pin
    client.set_needs_pin_reset(get_user(request))
    return http.HttpResponseRedirect(reverse('auth.logout'))


@user_verified
def reset_new_pin(request):
    form = forms.CreatePinForm()
    if request.method == 'POST':
        form = forms.CreatePinForm(uuid=get_user(request), data=request.POST)
        if form.is_valid():
            res = client.set_new_pin(form.buyer, form.cleaned_data['pin'])
            if form.handle_client_errors(res):
                set_user_has_pin(request, True)
                return http.HttpResponseRedirect(reverse('pin.reset_confirm'))
    return render(request, 'pin/reset_create.html', {'form': form})


@user_verified
def reset_confirm(request):
    form = forms.ConfirmPinForm()
    if request.method == 'POST':
        form = forms.ResetConfirmPinForm(uuid=get_user(request),
                                         data=request.POST)
        if form.is_valid():
            # Copy pin into place is handled in solitude, webpay
            # merely asked solitude to verify the new pin which
            # happens in validation of the form.
            return http.HttpResponseRedirect(get_payment_url())
    return render(request, 'pin/reset_confirm.html', {'form': form})


@user_verified
def reset_cancel(request):
    client.set_needs_pin_reset(get_user(request), False)
    return http.HttpResponseRedirect(reverse('pin.verify'))
