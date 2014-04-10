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
)
