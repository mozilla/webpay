from datetime import datetime

from django import http
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.views.decorators.debug import sensitive_post_parameters

from tower import ugettext as _

from lib.solitude.api import client
from lib.solitude.exceptions import ResourceModified
from webpay.auth.decorators import enforce_sequence, user_verified
from webpay.auth.utils import (get_user, set_user_has_confirmed_pin,
                               set_user_has_pin)
from webpay.base import dev_messages as msg
from webpay.base.logger import getLogger
from webpay.base.utils import system_error
from webpay.pay import get_wait_url
from . import forms

log = getLogger('w.pin')


@enforce_sequence
@sensitive_post_parameters('pin')
def create(request):
    form = forms.CreatePinForm()
    if request.method == 'POST':
        form = forms.CreatePinForm(uuid=get_user(request), data=request.POST)
        if form.is_valid():
            try:
                res = client.change_pin(form.uuid,
                                        pin=form.cleaned_data['pin'],
                                        etag=form.buyer_etag)
            except ResourceModified:
                return system_error(request, code=msg.RESOURCE_MODIFIED)

            if form.handle_client_errors(res):
                set_user_has_pin(request, True)
                return http.HttpResponseRedirect(reverse('pin.confirm'))
    form.no_pin = True
    return render(request, 'pin/pin_form.html', {'form': form,
                  'title': _('Create a Pin'),
                  'action': reverse('pin.create'),
                  'pin_form_tracking' : {
                      'pin_error_codes': form.pin_error_codes,
                  },
                  'track_cancel': {
                      'action': 'pin cancel',
                      'label': 'Create Pin Page',
                  }})


@enforce_sequence
@sensitive_post_parameters('pin')
def confirm(request):
    form = forms.ConfirmPinForm()
    if request.method == 'POST':
        form = forms.ConfirmPinForm(uuid=get_user(request), data=request.POST)
        if form.is_valid():
            set_user_has_confirmed_pin(request, True)
            return http.HttpResponseRedirect(get_wait_url(request))
    form.no_pin = True
    return render(request, 'pin/pin_form.html', {'form': form,
                  'title': _('Confirm Pin'),
                  'action': reverse('pin.confirm'),
                  'pin_form_tracking' : {
                    'pin_error_codes': form.pin_error_codes,
                  },
                  'track_cancel': {
                      'action': 'pin cancel',
                      'label': 'Confirm Pin Page',
                  }})


@enforce_sequence
@sensitive_post_parameters('pin')
def verify(request):
    form = forms.VerifyPinForm()

    if request.method == 'POST':
        form = forms.VerifyPinForm(uuid=get_user(request), data=request.POST)
        if form.is_valid():
            request.session['last_pin_success'] = datetime.now()
            return http.HttpResponseRedirect(get_wait_url(request))
        elif form.pin_is_locked:
            request.session['uuid_pin_is_locked'] = True
            return http.HttpResponseRedirect(reverse('pin.is_locked'))
    return render(request, 'pin/pin_form.html', {'form': form,
                  'title': _('Enter Pin'),
                  'action': reverse('pin.verify'),
                  'pin_form_tracking' : {
                    'pin_error_codes': form.pin_error_codes,
                  },
                  'track_cancel': {
                      'action': 'pin cancel',
                      'label': 'Verify Pin Page',
                  }})


@enforce_sequence
def is_locked(request):
    return render(request, 'pin/pin_is_locked.html')


@enforce_sequence
def was_locked(request):
    try:
        client.unset_was_locked(uuid=get_user(request))
    except ResourceModified:
        return system_error(request, code=msg.RESOURCE_MODIFIED)
    request.session['uuid_pin_was_locked'] = False
    return render(request, 'pin/pin_was_locked.html')


@enforce_sequence
@sensitive_post_parameters('pin')
def reset_start(request):
    request.session['was_reverified'] = False
    try:
        client.set_needs_pin_reset(get_user(request))
    except ResourceModified:
        return system_error(request, code=msg.RESOURCE_MODIFIED)
    request.session['uuid_needs_pin_reset'] = True
    form = forms.CreatePinForm()
    form.reset_flow = True
    return render(request, 'pin/reset_start.html',
                  {'title': _('Reset Pin'),
                   'action': reverse('pin.reset_new_pin'),
                   'form': form,
                   'track_cancel': {
                       'action': 'pin cancel',
                       'label': 'Reset Start Page',
                   }})


@enforce_sequence
@sensitive_post_parameters('pin')
def reset_new_pin(request):
    form = forms.CreatePinForm()
    if request.method == 'POST':
        form = forms.ResetPinForm(uuid=get_user(request), data=request.POST)
        if form.is_valid():
            try:
                res = client.set_new_pin(form.uuid, form.cleaned_data['pin'])
            except ResourceModified:
                return system_error(request, code=msg.RESOURCE_MODIFIED)
            if form.handle_client_errors(res):
                request.session['uuid_has_new_pin'] = True
                return http.HttpResponseRedirect(reverse('pin.reset_confirm'))

    form.reset_flow = True
    return render(request, 'pin/pin_form.html', {'form': form,
                  'title': _('Reset Pin'),
                  'action': reverse('pin.reset_new_pin'),
                  'pin_form_tracking' : {
                    'pin_error_codes': form.pin_error_codes,
                  },
                  'track_cancel': {
                      'action': 'pin cancel',
                      'label': 'Reset Pin page',
                  }})


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
            return http.HttpResponseRedirect(get_wait_url(request))
    form.reset_flow = True
    return render(request, 'pin/pin_form.html', {'form': form,
                  'title': _('Confirm Pin'),
                  'action': reverse('pin.reset_confirm'),
                  'pin_form_tracking' : {
                      'pin_error_codes': form.pin_error_codes,
                  },
                  'track_cancel': {
                      'action': 'pin cancel',
                      'label': 'Reset Pin page',
                  }})


@user_verified
def reset_cancel(request):
    try:
        client.set_needs_pin_reset(get_user(request), False)
    except ResourceModified:
        return system_error(request, code=msg.RESOURCE_MODIFIED)
    request.session['uuid_needs_pin_reset'] = False
    return http.HttpResponseRedirect(reverse('pin.verify'))
