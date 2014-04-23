from django.conf.urls.defaults import patterns, url

import views


urlpatterns = patterns(
    '',
    url(r'^(?P<provider_name>[^/]+)/success$', views.success,
        name='provider.success'),
    url(r'^(?P<provider_name>[^/]+)/error$', views.error,
        name='provider.error'),
    url(r'^(?P<provider_name>[^/]+)/notification$', views.notification,
        name='provider.notification'),
    url(r'^(?P<provider_name>[^/]+)/wait-to-finish$', views.wait_to_finish,
        name='provider.wait_to_finish'),
    url(r'^transaction/(?P<transaction_uuid>[^/]+)/status$',
        views.transaction_status, name='provider.transaction_status'),
)
