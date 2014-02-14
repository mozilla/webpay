from django.conf import settings
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

# Run jingo monkey patch - see https://github.com/jbalogh/jingo#forms
import jingo.monkey
jingo.monkey.patch()

urlpatterns = patterns('',
    (r'^mozpay/auth/', include('webpay.auth.urls')),
    (r'^mozpay/bango/', include('webpay.bango.urls')),
    (r'^mozpay/provider/', include('webpay.provider.urls')),
    (r'^mozpay/services/', include('webpay.services.urls')),
    (r'^mozpay/', include('webpay.pay.urls')),
    # When jsi18n is ready, re-enable this.
    #url('^mozpay/jsi18n.js$',
    #    cache_page(60 * 60 * 24 * 365)(javascript_catalog),
    #    {'domain': 'javascript', 'packages': ['webpay']}, name='jsi18n'),
    url(r'^mozpay/pin/', include('webpay.pin.urls'))
)

if settings.ENABLE_SPA:
    urlpatterns += patterns('',
        url(r'^mozpay/v1/api/', include('webpay.api.urls', namespace='api'))
    )

# Test/Development only urls.
if settings.TEMPLATE_DEBUG:
    urlpatterns += patterns('',
        url(r'^', include('webpay.testing.urls')),
    )

# Ensure that 403 is routed through a view.
handler403 = 'webpay.auth.views.denied'
