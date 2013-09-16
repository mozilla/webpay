from django import forms
from django.conf import settings

import jwt
from django_paranoia.forms import ParanoidForm

from mozpay.exc import InvalidJWT
from mozpay.verify import verify_jwt
from webpay.base.logger import getLogger
from webpay.pay.utils import lookup_issuer, UnknownIssuer

log = getLogger('w.services')


class SigCheckForm(ParanoidForm):
    sig_check_jwt = forms.CharField()

    def clean_sig_check_jwt(self):
        enc_jwt = self.cleaned_data['sig_check_jwt'].encode('ascii', 'ignore')
        try:
            jwt_data = jwt.decode(enc_jwt, verify=False)
        except jwt.DecodeError, exc:
            log.info('caught sig_check exc: {0.__class__.__name__}: {0}'
                     .format(exc))
            raise forms.ValidationError('INVALID_JWT_OR_UNKNOWN_ISSUER')

        try:
            secret, active_product = lookup_issuer(jwt_data.get('iss', ''))
        except UnknownIssuer, exc:
            log.info('caught sig_check exc: {0.__class__.__name__}: {0}'
                     .format(exc))
            raise forms.ValidationError('INVALID_JWT_OR_UNKNOWN_ISSUER')

        try:
            clean_jwt = verify_jwt(enc_jwt,
                                   settings.DOMAIN,  # JWT audience.
                                   secret,
                                   required_keys=[])
        except InvalidJWT, exc:
            log.info('caught sig_check exc: {0.__class__.__name__}: {0}'
                     .format(exc))
            raise forms.ValidationError('INVALID_JWT_OR_UNKNOWN_ISSUER')

        if clean_jwt.get('typ', '') != settings.SIG_CHECK_TYP:
            raise forms.ValidationError('INCORRECT_JWT_TYP')

        return clean_jwt


class ErrorLegendForm(ParanoidForm):
    locale = forms.TypedChoiceField(
                required=False,
                # TODO: maybe support more standard language codes and/or
                # handle short code conversion?
                choices=zip(settings.PROD_LANGUAGES,
                            settings.PROD_LANGUAGES))
