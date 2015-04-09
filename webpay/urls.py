from django.conf import settings
from django.conf.urls.defaults import patterns, include, url

from webpay.spa.views import index


# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

# Run jingo monkey patch - see https://github.com/jbalogh/jingo#forms
import jingo.monkey
jingo.monkey.patch()

urlpatterns = patterns(
    '',
    url(r'^mozpay/$', index, name='index'),
    url(r'^mozpay/v1/api/', include('webpay.api.urls', namespace='api')),
    url(r'^mozpay/spa/', include('webpay.spa.urls', namespace='spa')),
    (r'^mozpay/auth/', include('webpay.auth.urls')),
    (r'^mozpay/bango/', include('webpay.bango.urls')),
    (r'^mozpay/provider/', include('webpay.provider.urls')),
    (r'^mozpay/services/', include('webpay.services.urls')),
)

# Ensure that 403 is routed through a view.
handler403 = 'webpay.auth.views.denied'


if settings.DEBUG:

    from django.views.defaults import (
        page_not_found,
        permission_denied,
        server_error,
    )

    urlpatterns += patterns(
        '',
        url(r'^403$', permission_denied, name="error_403"),
        url(r'^404$', page_not_found, name="error_404"),
        url(r'^500$', server_error, name="error_500"),
    )
