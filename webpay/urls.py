from django.conf import settings
from django.conf.urls.defaults import patterns, include, url

from webpay.spa.views import index as spa_index
from webpay.spa.views import wait_to_finish as spa_wait_to_finish

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

if settings.ENABLE_SPA_URLS:
    urlpatterns += patterns('',
        url(r'^mozpay/spa/(?P<provider_name>[^/]+)/wait-to-finish', spa_wait_to_finish, name='spa_wait_to_finish'),
        url(r'^mozpay/spa/(?:' + '|'.join(settings.SPA_URLS) + ')$', spa_index),
        url(r'^mozpay/v1/api/', include('webpay.api.urls', namespace='api'))
    )

# Test/Development only urls.
if settings.TEMPLATE_DEBUG:
    urlpatterns += patterns('',
        url(r'^', include('webpay.testing.urls')),
    )

# Ensure that 403 is routed through a view.
handler403 = 'webpay.auth.views.denied'
