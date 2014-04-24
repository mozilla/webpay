from django import http
from django.core.urlresolvers import reverse
from django.conf import settings
from django.shortcuts import render

from tower import ugettext as _

from webpay.pin import forms


def test_pin_ui(request):
    """View just for visually testing the pin UI.

    DEV ONLY.

    """

    if not settings.TEMPLATE_DEBUG or not settings.DEBUG:
        return http.HttpResponseForbidden()

    form = forms.CreatePinForm()

    return render(request, 'pin/pin_form.html', {
        'form': form,
        'title': _('Create a Pin'),
        'action': reverse('pin.create'),
        'pin_form_tracking' : {
            'pin_error_codes': form.pin_error_codes,
        },
        'track_cancel': {
            'action': 'pin cancel',
            'label': 'Create Pin Page',
        }
    })

