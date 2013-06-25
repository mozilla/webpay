from django.conf.urls.defaults import patterns, url

import views

urlpatterns = patterns('',  # noqa
    url(r'^denied$', views.denied, name='auth.denied'),
    url(r'^reset_user$', views.reset_user, name='auth.reset_user'),
    url(r'^verify$', views.verify, name='auth.verify'),
    url(r'^reverify$', views.reverify, name='auth.reverify'),
)
