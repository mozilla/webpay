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
    (r'^mozpay/pin/', include('webpay.pin.urls')),
    (r'^mozpay/', include('webpay.pay.urls'))
)

if settings.SPA_ENABLE_URLS:
    urlpatterns += patterns('',
        url(r'^mozpay/spa/', include('webpay.spa.urls', namespace='spa')),
        url(r'^mozpay/v1/api/', include('webpay.api.urls', namespace='api'))
    )

# Ensure that 403 is routed through a view.
handler403 = 'webpay.auth.views.denied'
