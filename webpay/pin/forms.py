from datetime import datetime

from django import forms
from django.conf import settings
from django.forms.util import ErrorList
from django.forms.widgets import TextInput
from django.views.decorators.debug import sensitive_variables

from django_paranoia.forms import ParanoidForm

from lib.solitude.api import client

from webpay.base import dev_messages as msg
from webpay.base.logger import getLogger

log = getLogger('w.pin')


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
        self._pin_error_codes.add(key)

    def append_to_errors(self, field, error):
        # Solitude returns error codes as messages so expose those:
        for code in error:
            self.add_error_code(code)
        if field in self._errors:
            self._errors[field].append(error)
        else:
            self._errors[field] = ErrorList(error)

    def client_response_is_valid(self, response):
        """
        Analyzes the response from the API client (to Solitude),
        turns errors into Django form errors, and returns True if valid (no
        errors)

        :param response: A dictionary returned from the solitude client API.
        :rtype: True if there are no errors, otherwise False.
        """
        if not isinstance(response, dict):
            # This handles verify which returns a bool.
            return response
        errors = response.get('errors')
        if errors:
            for field, error in errors.iteritems():
                # Solitude returns some pin errors under 'new_pin' rather
                # than 'pin' so we ensure these are associated with the pin
                # field too.
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
        if buyer and self.client_response_is_valid(buyer):
            try:
                self.buyer_etag = buyer['etag']
            except KeyError:
                self.buyer_etag = ''
            if buyer.get('pin'):
                self.add_error_code(msg.PIN_ALREADY_CREATED)
                raise forms.ValidationError(msg.PIN_ALREADY_CREATED)
        return pin


class VerifyPinForm(BasePinForm):

    @sensitive_variables('pin')
    def clean_pin(self, *args, **kwargs):
        pin = self.cleaned_data['pin']
        res = client.verify_pin(self.uuid, pin)
        self.pin_is_locked = False
        if self.client_response_is_valid(res):
            if res.get('locked'):
                self.pin_is_locked = True
                # Not displayed to the user.
                raise forms.ValidationError('pin locked')
            elif res.get('valid'):
                return pin

        self.add_error_code(msg.WRONG_PIN)
        raise forms.ValidationError(msg.WRONG_PIN)


class ResetPinForm(BasePinForm):

    def __init__(self, *args, **kw):
        # We need to validate the user_reset info stored in this user's session
        self.user_reset = kw.pop('user_reset')
        super(ResetPinForm, self).__init__(*args, **kw)

    @sensitive_variables('pin')
    def clean_pin(self, *args, **kwargs):
        pin = self.cleaned_data['pin']
        self._ensure_user_reauthenticated()
        buyer = client.get_buyer(self.uuid)
        if buyer and self.client_response_is_valid(buyer):
            self.buyer = buyer
        return pin

    def _ensure_user_reauthenticated(self):
        """
        Check that the user re-authenticated with Firefox Accounts
        sometime after they requested the PIN reset.
        """

        reauth_ok = False
        log.info('PIN reset: user_reset from session: {reset}'
                 .format(reset=self.user_reset))
        if self.user_reset:
            start_ts = self.user_reset.get('start_ts')
            fxa_auth_ts = self.user_reset.get('fxa_auth_ts')
        else:
            start_ts = None
            fxa_auth_ts = None

        if not self.user_reset:
            log.warning('PIN reset error: user_reset not in session')
        elif not start_ts:
            log.warning('PIN reset error: user_reset[start_ts] not in session')
        elif not fxa_auth_ts:
            log.warning(
                'PIN reset error: user_reset[fxa_auth_ts] not in session')
            if not settings.REQUIRE_REAUTH_TS_FOR_PIN_RESET:
                log.warning('missing fxa_auth_ts ignored for PIN reset')
                reauth_ok = True
        elif fxa_auth_ts < start_ts:
            log.warning(
                'PIN reset error: fxa_auth_ts {f} occurred before reset {r}'
                .format(f=datetime.utcfromtimestamp(fxa_auth_ts),
                        r=datetime.utcfromtimestamp(start_ts)))
        elif fxa_auth_ts > (start_ts + settings.FXA_PIN_REAUTH_EXPIRY):
            log.warning(
                'PIN reset error: fxa_auth_ts {f} has expired. '
                'Reset start was: {r}'
                .format(f=datetime.utcfromtimestamp(fxa_auth_ts),
                        r=datetime.utcfromtimestamp(start_ts)))
        else:
            reauth_ok = True

        if not reauth_ok:
            self.add_error_code(msg.INVALID_PIN_REAUTH)
            raise forms.ValidationError(msg.INVALID_PIN_REAUTH)
