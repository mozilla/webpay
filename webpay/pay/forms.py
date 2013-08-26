from django import forms
from django.conf import settings

from django_paranoia.forms import ParanoidForm
import jwt
from tower import ugettext as _

from lib.solitude.constants import ACCESS_SIMULATE

from webpay.base.logger import getLogger

from .utils import lookup_issuer, UnknownIssuer

log = getLogger('w.pay')


class VerifyForm(ParanoidForm):
    req = forms.CharField()
    key = settings.KEY
    secret = settings.SECRET
    is_simulation = False

    def clean_req(self):
        data = self.cleaned_data['req']
        jwt_data = data.encode('ascii', 'ignore')
        log.debug('incoming JWT data: %r' % jwt_data)
        try:
            payload = jwt.decode(jwt_data, verify=False)
        except jwt.DecodeError, exc:
            # L10n: first argument is a detailed error message.
            err = _('Error decoding JWT: {0}').format(exc)
            raise forms.ValidationError(err)
        log.debug('Received JWT: %r' % payload)
        if not isinstance(payload, dict):
            # It seems that some JWT libs are encoding strings of JSON
            # objects, not actual objects. For now we treat this as an
            # error. If it becomes a headache for developers we can make a
            # guess and check the string for a JSON object.
            log.info('JWT was not a dict, it was %r' % type(payload))
            raise forms.ValidationError(
                # L10n: first argument is a data type, such as <unicode>
                _('The JWT did not decode to a JSON object. Its type was {0}.')
                .format(type(payload)))

        try:
            sim = payload['request']['simulate']
        except KeyError:
            sim = False
        self.is_simulation = bool(sim) and isinstance(sim, dict)
        if self.is_simulation and not settings.ALLOW_SIMULATE:
            raise forms.ValidationError(
                _('Payment simulations are disabled at this time.'))

        if self.is_simulation:
            # Validate simulations.
            if sim.get('result') not in settings.ALLOWED_SIMULATIONS:
                raise forms.ValidationError(
                    _('The requested simulation result is not supported.'))
            if sim['result'] == 'chargeback' and not sim.get('reason'):
                raise forms.ValidationError(
                    _("The requested chargeback simulation is missing the "
                      "key '{0}'.").format('reason'))

        self.key = payload.get('iss', '')
        try:
            self.secret, active_product = lookup_issuer(self.key)
        except UnknownIssuer, err:
            raise forms.ValidationError(
                # L10n: the first argument is a key to identify an issuer.
                _('No one has been registered for JWT issuer {0}.')
                .format(repr(self.key)))

        if (active_product and active_product['access'] == ACCESS_SIMULATE
            and not self.is_simulation):
            raise forms.ValidationError(
                # L10n: the first argument is a key to identify an issuer.
                _('This payment key, {0}, can only be used to simulate '
                  'purchases.').format(repr(self.key)))

        icons = payload['request'].get('icons', None)
        if icons and type(icons) != dict:
            example = '{"64": "https://.../icon_64.png"}'
            raise forms.ValidationError(
                    # L10n: First argument is the name of a key. Second
                    # argument is an example of the proper key format.
                    _('The "{0}" key must be an object of '
                      'URLs such as {1}').format('icons', example))

        max_size = settings.SHORT_FIELD_MAX_LENGTH
        for fn in ('chargebackURL',
                   'defaultLocale',
                   'id',
                   'name',
                   'postbackURL',
                   'productData'):
            if len(payload['request'].get(fn, '')) > max_size:
                raise forms.ValidationError(
                        # L10n: First argument is the name of a key. Second
                        # argument is a number.
                        _('The value for key "{0}" exceeds the maximum '
                          'length of {1}').format(fn, max_size))

        if payload['request'].get('locales'):
            if not payload['request'].get('defaultLocale'):
                raise forms.ValidationError(
                    # L10n: First and second arguements are the names of keys.
                    _('If {0} is defined, then you must also define {1}.')
                        .format('locales', 'defaultLocale'))

        return data
