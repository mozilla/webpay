from lib.solitude import constants


TYP_POSTBACK = 'mozilla/payments/pay/postback/v1'
TYP_CHARGEBACK = 'mozilla/payments/pay/chargeback/v1'

TYPE_STRINGS = {
    constants.TYPE_PAYMENT: TYP_POSTBACK,
    constants.TYPE_REFUND: TYP_CHARGEBACK
}
