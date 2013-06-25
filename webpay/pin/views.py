from datetime import datetime

from django import http
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.views.decorators.debug import sensitive_post_parameters

from tower import ugettext as _

from lib.solitude.api import client
from webpay.auth.decorators import (enforce_sequence, require_reverification,
                                    user_verified)
from webpay.auth.utils import (get_user, set_user_has_confirmed_pin,
                               set_user_has_pin)
from webpay.base.logger import getLogger
from webpay.pay import get_payment_url
from . import forms

log = getLogger('w.pin')


@enforce_sequence
@sensitive_post_parameters('pin')
def create(request):
    form = forms.CreatePinForm()
    if request.method == 'POST':
        form = forms.CreatePinForm(uuid=get_user(request), data=request.POST)
        if form.is_valid():
            if getattr(form, 'buyer_exists', False):
                res = client.change_pin(form.uuid, form.cleaned_data['pin'])
            else:
                res = client.create_buyer(form.uuid, form.cleaned_data['pin'])
            if form.handle_client_errors(res):
                set_user_has_pin(request, True)
                return http.HttpResponseRedirect(reverse('pin.confirm'))
    form.no_pin = True
    return render(request, 'pin/pin_form.html', {'form': form,
                  'title': _('Create a Pin'),
                  'action': reverse('pin.create')})


@enforce_sequence
@sensitive_post_parameters('pin')
def confirm(request):
    form = forms.ConfirmPinForm()
    if request.method == 'POST':
        form = forms.ConfirmPinForm(uuid=get_user(request), data=request.POST)
        if form.is_valid():
            set_user_has_confirmed_pin(request, True)
            return http.HttpResponseRedirect(get_payment_url())
    form.no_pin = True
    return render(request, 'pin/pin_form.html', {'form': form,
                  'title': _('Confirm Pin'),
                  'action': reverse('pin.confirm')})


@enforce_sequence
@sensitive_post_parameters('pin')
def verify(request):
    form = forms.VerifyPinForm()

    if request.method == 'POST':
        form = forms.VerifyPinForm(uuid=get_user(request), data=request.POST)
        if form.is_valid():
            request.session['last_pin_success'] = datetime.now()
            return http.HttpResponseRedirect(get_payment_url())
        elif form.pin_is_locked:
            request.session['uuid_pin_is_locked'] = True
            return http.HttpResponseRedirect(reverse('pin.is_locked'))
    return render(request, 'pin/pin_form.html', {'form': form,
                  'title': _('Enter Pin'),
                  'action': reverse('pin.verify')})


@enforce_sequence
def is_locked(request):
    return render(request, 'pin/pin_is_locked.html')


@enforce_sequence
def was_locked(request):
    request.session['uuid_pin_was_locked'] = False
    return render(request, 'pin/pin_was_locked.html')


@enforce_sequence
@sensitive_post_parameters('pin')
def reset_start(request):
    request.session['was_reverified'] = False
    client.set_needs_pin_reset(get_user(request))
    request.session['uuid_needs_pin_reset'] = True
    form = forms.CreatePinForm()
    form.reset_flow = True
    return render(request, 'pin/reset_start.html',
                  {'title': _('Reset Pin'),
                   'action': reverse('pin.reset_new_pin'),
                   'form': form})


@require_reverification
@enforce_sequence
@sensitive_post_parameters('pin')
def reset_new_pin(request):
    form = forms.CreatePinForm()
    if request.method == 'POST':
        form = forms.ResetPinForm(uuid=get_user(request), data=request.POST)
        if form.is_valid():
            res = client.set_new_pin(form.uuid, form.cleaned_data['pin'])
            if form.handle_client_errors(res):
                request.session['uuid_has_new_pin'] = True
                return http.HttpResponseRedirect(reverse('pin.reset_confirm'))

    form.reset_flow = True
    return render(request, 'pin/pin_form.html', {'form': form,
                  'title': _('Reset Pin'),
                  'action': reverse('pin.reset_new_pin')})


@require_reverification
@enforce_sequence
@sensitive_post_parameters('pin')
def reset_confirm(request):
    form = forms.ConfirmPinForm()
    if request.method == 'POST':
        form = forms.ResetConfirmPinForm(uuid=get_user(request),
                                         data=request.POST)
        if form.is_valid():
            # Clear reverification state since this PIN reset is finished.
            request.session['was_reverified'] = False
            messages.success(request, _('Pin reset'))
            # Copy pin into place is handled in solitude, webpay
            # merely asked solitude to verify the new pin which
            # happens in validation of the form.
            return http.HttpResponseRedirect(get_payment_url())
    form.reset_flow = True
    return render(request, 'pin/pin_form.html', {'form': form,
                  'title': _('Confirm Pin'),
                  'action': reverse('pin.reset_confirm')})


@user_verified
def reset_cancel(request):
    client.set_needs_pin_reset(get_user(request), False)
    request.session['uuid_needs_pin_reset'] = False
    return http.HttpResponseRedirect(reverse('pin.verify'))
