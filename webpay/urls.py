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
    url(r'^mozpay/pin/', include('webpay.pin.urls')),
    # This is served by marketplace.
    # (r'^robots\.txt$',
    #  lambda r: HttpResponse(
    #      "User-agent: *\n%s: /" % (
    #          'Allow' if settings.ENGAGE_ROBOTS else 'Disallow'
    #      ),
    #      mimetype="text/plain"
    #  )
    # ),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

# Test/Development only urls.
if settings.TEMPLATE_DEBUG:
    urlpatterns += patterns('',
        url(r'^', include('webpay.testing.urls')),
    )
