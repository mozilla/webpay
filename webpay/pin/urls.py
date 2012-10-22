from django.conf.urls.defaults import patterns, url

from . import views


urlpatterns = patterns('',
    url(r'^create', views.create, name='pin_create'),
    url(r'^verify', views.verify, name='pin_verify'),
    url(r'^change', views.change, name='pin_change'),
)
