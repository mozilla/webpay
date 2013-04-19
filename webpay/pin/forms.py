from django import forms
from django.forms.util import ErrorList
from django.views.decorators.debug import sensitive_variables

from tower import ugettext_lazy as _

from lib.solitude.api import client


class BasePinForm(forms.Form):
    pin = forms.CharField(max_length=4, required=True)

    def __init__(self, uuid=None, *args, **kwargs):
        self.uuid = uuid
        super(BasePinForm, self).__init__(*args, **kwargs)
        self.fields['pin'].widget.attrs.update({
            'autocomplete': 'off',
            'type': 'number',
        })

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
            self.buyer = buyer
            if buyer.get('pin'):
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
                raise forms.ValidationError(_('Your PIN was entered '
                                              'incorrectly too many times. '
                                              'Sign in to continue.'))
            elif res.get('valid'):
                return pin

        raise forms.ValidationError(_('Wrong pin'))


class ConfirmPinForm(BasePinForm):

    @sensitive_variables('pin')
    def clean_pin(self, *args, **kwargs):
        pin = self.cleaned_data['pin']
        if self.handle_client_errors(client.confirm_pin(self.uuid, pin)):
            return pin

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

        raise forms.ValidationError(_("Pins do not match."))
