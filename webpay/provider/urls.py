from django.conf.urls.defaults import patterns, url

import views


urlpatterns = patterns('',
    url(r'^success$', views.success, name='provider.success'),
    url(r'^error$', views.error, name='provider.error'),
)
