from django import forms
from django.conf import settings

from gelato.constants import base
import jwt
from tower import ugettext as _

from models import InappConfig


class VerifyForm(forms.Form):
    req = forms.CharField()
    key = settings.KEY
    secret = settings.SECRET

    def clean_req(self):
        data = self.cleaned_data['req']
        try:
            payload = jwt.decode(data.encode('ascii', 'ignore'), verify=False)
        except jwt.DecodeError, exc:
            # L10n: first argument is a detailed error message.
            err = _('Error decoding JWT: {0}').format(exc)
            raise forms.ValidationError(err)
        if not isinstance(payload, dict):
            # It seems that some JWT libs are encoding strings of JSON
            # objects, not actual objects. For now we treat this as an
            # error. If it becomes a headache for developers we can make a
            # guess and check the string for a JSON object.
            raise forms.ValidationError(
                # L10n: first argument is a data type, such as <unicode>
                _('The JWT did not decode to a JSON object. Its type was {0}.')
                .format(type(payload)))

        app_id = payload.get('iss', '')
        if app_id == settings.KEY:
            # This is an app purchase because it matches the settings.
            self.key, self.secret = app_id, settings.SECRET
        else:
            # In app config, go look it up.
            try:
                cfg = InappConfig.objects.get(public_key=app_id,
                                              addon__status=base.STATUS_PUBLIC)
            except InappConfig.DoesNotExist:
                raise forms.ValidationError(_('InappConfig does not exist.'))
            self.key, self.secret = app_id, cfg.get_private_key()

        return data
