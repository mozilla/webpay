from django.conf.urls.defaults import patterns, url

import views

urlpatterns = patterns('',
    url(r'^monitor$', views.monitor, name='monitor'),
)

