from django import forms
from django.forms.util import ErrorList
from django.forms.widgets import TextInput
from django.views.decorators.debug import sensitive_variables

from django_paranoia.forms import ParanoidForm
from tower import ugettext_lazy as _

from lib.solitude.api import client

from webpay.pay.constants import PIN_ERROR_CODES


class HTML5NumberWidget(TextInput):
    """An HTML5 number input widget."""
    input_type = 'number'


class BasePinForm(ParanoidForm):
    pin = forms.CharField(max_length=4, required=True,
                          widget=HTML5NumberWidget)

    def __init__(self, uuid=None, *args, **kwargs):
        # Error codes for tracking see pay/constants.py.
        self._pin_error_codes = set()
        self.uuid = uuid
        super(BasePinForm, self).__init__(*args, **kwargs)
        self.fields['pin'].widget.attrs.update({
            'autocomplete': 'off',
            'max': '9999',
            'placeholder': '****',
            # Digit only keyboard for B2G (bug 820268).
            'x-inputmode': 'digit',
        })

    @property
    def pin_error_codes(self):
        return list(self._pin_error_codes)

    def add_error_code(self, key):
        if key in PIN_ERROR_CODES:
            self._pin_error_codes.add(key)

    def append_to_errors(self, field, error):
        if field in self._errors:
            self._errors[field].append(error)
        else:
            self._errors[field] = ErrorList(error)

    def handle_client_errors(self, response):
        """Checks to see if the response has errors on it and propagates it to
        the form.

        :param response: A dictionary returned from the solitude client API.
        :rtype: True if there are no errors, otherwise False.
        """
        if not isinstance(response, dict):
            # This handles verify which returns a bool.
            return response
        errors = response.get('errors')
        if errors:
            for field, error in errors.iteritems():
                # Solitude returns some pin errors under 'new_pin' rather than 'pin'
                # so we ensure these are associated with the pin field too.
                if field == 'new_pin':
                    field = 'pin'
                if field in self.fields:
                    self.append_to_errors(field, error)
                else:
                    self.append_to_errors('__all__', '%s: %s' % (field, error))
            return False
        return True


class CreatePinForm(BasePinForm):

    @sensitive_variables('pin')
    def clean_pin(self, *args, **kwargs):
        pin = self.cleaned_data['pin']
        buyer = client.get_buyer(self.uuid)
        if buyer and self.handle_client_errors(buyer):
            try:
                self.buyer_etag = buyer['etag']
            except KeyError:
                self.buyer_etag = ''
            if buyer.get('pin'):
                self.add_error_code('PIN_ALREADY_CREATED')
                raise forms.ValidationError(
                    _('You have already created a PIN.')
                )
        return pin


class VerifyPinForm(BasePinForm):

    @sensitive_variables('pin')
    def clean_pin(self, *args, **kwargs):
        pin = self.cleaned_data['pin']
        res = client.verify_pin(self.uuid, pin)
        self.pin_is_locked = False
        if self.handle_client_errors(res):
            if res.get('locked'):
                self.pin_is_locked = True
                # Not displayed to the user.
                raise forms.ValidationError('pin locked')
            elif res.get('valid'):
                return pin

        self.add_error_code('WRONG_PIN')
        raise forms.ValidationError(_('Wrong pin'))


class ConfirmPinForm(BasePinForm):

    @sensitive_variables('pin')
    def clean_pin(self, *args, **kwargs):
        pin = self.cleaned_data['pin']
        if self.handle_client_errors(client.confirm_pin(self.uuid, pin)):
            return pin

        self.add_error_code('PINS_DONT_MATCH')
        raise forms.ValidationError(_("Pins do not match."))


class ResetPinForm(BasePinForm):

    @sensitive_variables('pin')
    def clean_pin(self, *args, **kwargs):
        pin = self.cleaned_data['pin']
        buyer = client.get_buyer(self.uuid)
        if buyer and self.handle_client_errors(buyer):
            self.buyer = buyer
        return pin


class ResetConfirmPinForm(BasePinForm):

    @sensitive_variables('pin')
    def clean_pin(self, *args, **kwargs):
        pin = self.cleaned_data['pin']
        if self.handle_client_errors(client.reset_confirm_pin(self.uuid, pin)):
            return pin

        self.add_error_code('PINS_DONT_MATCH')
        raise forms.ValidationError(_("Pins do not match."))
