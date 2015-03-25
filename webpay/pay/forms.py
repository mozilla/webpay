import json

from django import forms
from django.conf import settings

from django_paranoia.forms import ParanoidForm
import jwt

from lib.solitude.constants import ACCESS_SIMULATE
from tower import ugettext_lazy as _

from webpay.base import dev_messages as msg
from webpay.base.logger import getLogger

from .utils import lookup_issuer, UnknownIssuer

log = getLogger('w.pay')


class NetCodeForm(ParanoidForm):
    mcc = forms.RegexField(regex='^\d{2,3}$', required=True)
    mnc = forms.RegexField(regex='^\d{2,3}$', required=True)


class VerifyForm(ParanoidForm):
    req = forms.CharField()
    # If mcc or mnc are given, we'll accept any value that conforms to the
    # format. We'll then whitelist actions on particular values.
    mcc = forms.RegexField(regex='^\d{2,3}$', required=False)
    mnc = forms.RegexField(regex='^\d{2,3}$', required=False)
    key = settings.KEY
    secret = settings.SECRET
    is_simulation = False

    def clean(self):
        cleaned_data = super(VerifyForm, self).clean()
        # If we set mnc but not mcc or vice versa.
        if bool(cleaned_data.get('mnc')) != bool(cleaned_data.get('mcc')):
            raise forms.ValidationError('Both mnc and mcc are required to be '
                                        'present or not.')
        return cleaned_data

    def clean_req(self):
        data = self.cleaned_data['req']
        jwt_data = data.encode('ascii', 'ignore')
        log.debug('incoming JWT data: %r' % jwt_data)
        try:
            payload = jwt.decode(jwt_data, verify=False)
        except jwt.DecodeError, exc:
            log.debug('Error decoding JWT: {0}'.format(exc))
            raise forms.ValidationError(msg.JWT_DECODE_ERR)
        log.debug('Received JWT: %r' % payload)
        if not isinstance(payload, dict):
            # It seems that some JWT libs are encoding strings of JSON
            # objects, not actual objects. For now we treat this as an
            # error. If it becomes a headache for developers we can make a
            # guess and check the string for a JSON object.
            log.info('JWT was not a dict, it was %r' % type(payload))
            raise forms.ValidationError(msg.INVALID_JWT_OBJ)

        # The decode method already parses the header like this
        # but does not give us access to it so we need to re-parse it.
        header = json.loads(jwt.base64url_decode(jwt_data.split('.')[0]))
        if header['alg'] not in settings.SUPPORTED_JWT_ALGORITHMS:
            log.debug(
                'JWT header alg is {alg} which is not supported. JWT: {jwt}'
                .format(alg=header['alg'], jwt=jwt_data))
            raise forms.ValidationError(msg.INVALID_JWT_OBJ)

        try:
            sim = payload['request']['simulate']
        except KeyError:
            sim = False
        self.is_simulation = bool(sim) and isinstance(sim, dict)
        if self.is_simulation and not settings.ALLOW_SIMULATE:
            raise forms.ValidationError(msg.SIM_DISABLED)

        if self.is_simulation:
            # Validate simulations.
            if sim.get('result') not in settings.ALLOWED_SIMULATIONS:
                raise forms.ValidationError(msg.BAD_SIM_RESULT)
            if sim['result'] == 'chargeback' and not sim.get('reason'):
                log.info("chargeback simulation is missing the "
                         "key '{0}'.".format('reason'))
                raise forms.ValidationError(msg.NO_SIM_REASON)

        self.key = payload.get('iss', '')
        try:
            self.secret, active_product = lookup_issuer(self.key)
        except UnknownIssuer:
            log.info('No one registered for JWT issuer {0}'
                     .format(repr(self.key)))
            raise forms.ValidationError(msg.BAD_JWT_ISSUER)

        if (active_product and active_product['access'] == ACCESS_SIMULATE
                and not self.is_simulation):
            log.info('payment key {0} can only simulate, tried to purchase'
                     .format(repr(self.key)))
            raise forms.ValidationError(msg.SIM_ONLY_KEY)

        icons = payload['request'].get('icons', None)
        if icons and type(icons) != dict:
            raise forms.ValidationError(msg.BAD_ICON_KEY)

        for fn in msg.SHORT_FIELDS:
            # These fields might be NULL so make sure they are strings:
            if (len(payload['request'].get(fn, None) or '') >
                    settings.SHORT_FIELD_MAX_LENGTH):
                raise forms.ValidationError(msg.SHORT_FIELD_TOO_LONG_CODE[fn])

        if payload['request'].get('locales'):
            if not payload['request'].get('defaultLocale'):
                raise forms.ValidationError(msg.NO_DEFAULT_LOC)

        return data


class SuperSimulateForm(ParanoidForm):
    action = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices=(('real', _('Make a real payment')),
                 ('simulate', _('Simulate a payment'))),
        initial='real')
    network = forms.ChoiceField(required=False,
                                choices=(('', _('Default network')),
                                         # Choice key is mcc:mnc.
                                         ('334:020', 'Mexico: AMX')))

    def clean_network(self):
        network = self.cleaned_data.get('network')
        if not network:
            return None
        return network.split(':')  # -> (mcc, mnc)
