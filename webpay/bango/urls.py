from django.conf.urls.defaults import patterns, url

import views

urlpatterns = patterns(
    '',
    url(r'^success$', views.success, name='bango.success'),
    url(r'^error$', views.error, name='bango.error'),
    url(r'^notification$', views.notification, name='bango.notification'),
)
