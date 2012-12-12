from django import forms
from django.forms.util import ErrorList

from tower import ugettext_lazy as _

from lib.solitude.api import client


class BasePinForm(forms.Form):
    pin = forms.CharField(max_length=4, required=True)

    def __init__(self, uuid=None, *args, **kwargs):
        self.uuid = uuid
        super(BasePinForm, self).__init__(*args, **kwargs)

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
                if field in self.fields:
                    self.append_to_errors(field, error)
                else:
                    self.append_to_errors('__all__', '%s: %s' % (field, error))
            return False
        return True


class CreatePinForm(BasePinForm):

    def clean_pin(self, *args, **kwargs):
        pin = self.cleaned_data['pin']
        buyer = client.get_buyer(self.uuid)
        if buyer and self.handle_client_errors(buyer):
            self.buyer = buyer
            if buyer.get('pin'):
                raise forms.ValidationError(_('Buyer already has a PIN.'))
        return pin


class VerifyPinForm(BasePinForm):

    def clean_pin(self, *args, **kwargs):
        pin = self.cleaned_data['pin']
        if self.handle_client_errors(client.verify_pin(self.uuid, pin)):
            return pin

        raise forms.ValidationError(_('Incorrect PIN.'))


class ConfirmPinForm(BasePinForm):

    def clean_pin(self, *args, **kwargs):
        pin = self.cleaned_data['pin']
        if self.handle_client_errors(client.confirm_pin(self.uuid, pin)):
            return pin

        raise forms.ValidationError(_('Incorrect PIN.'))


class ChangePinForm(BasePinForm):
    old_pin = forms.CharField(max_length=4, required=True)

    def clean_old_pin(self, *args, **kwargs):
        old_pin = self.cleaned_data['old_pin']
        if self.handle_client_errors(client.verify_pin(self.uuid, old_pin)):
            self.buyer = self.handle_client_errors(client.get_buyer(self.uuid))
            return old_pin
        raise forms.ValidationError(_('Incorrect PIN'))
