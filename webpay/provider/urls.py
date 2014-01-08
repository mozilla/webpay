from django.conf.urls.defaults import patterns, url

import views


urlpatterns = patterns('',
    url(r'^(?P<provider>[^/]+)/success$', views.success,
        name='provider.success'),
    url(r'^(?P<provider>[^/]+)/error$', views.error,
        name='provider.error'),
)
