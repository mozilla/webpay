from django import forms

from tower import ugettext_lazy as _

from lib.solitude.api import client


class BasePinForm(forms.Form):

    def __init__(self, uuid=None, *args, **kwargs):
        self.uuid = uuid
        super(BasePinForm, self).__init__(*args, **kwargs)


class CreatePinForm(BasePinForm):
    pin = forms.CharField(max_length=4, required=True)

    def clean_pin(self, *args, **kwargs):
        pin = self.cleaned_data['pin']
        buyer = client.get_buyer(self.uuid)
        if buyer:
            self.buyer = buyer
            if buyer.get('pin'):
                raise forms.ValidationError(_('Buyer already has a PIN.'))
        return pin


class VerifyPinForm(BasePinForm):
    pin = forms.CharField(max_length=4, required=True)

    def clean_pin(self, *args, **kwargs):
        pin = self.cleaned_data['pin']
        if client.verify_pin(self.uuid, pin):
            return pin

        raise forms.ValidationError(_('Incorrect PIN.'))


class ChangePinForm(BasePinForm):
    old_pin = forms.CharField(max_length=4, required=True)
    new_pin = forms.CharField(max_length=4, required=True)

    def clean_old_pin(self, *args, **kwargs):
        old_pin = self.cleaned_data['old_pin']
        if client.verify_pin(self.uuid, old_pin):
            return old_pin
        raise forms.ValidationError(_('Incorrect PIN'))
