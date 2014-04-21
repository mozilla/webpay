# This is really sucky, but the countries are returned from the zamboni API
# as numbers. Fortunately for the moment we only care about one.
#
# This is a mapping of MCC to zamboni region id.
COUNTRIES = {
    '334': 12,  # Mexico
}
