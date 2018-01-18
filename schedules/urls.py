from django.conf.urls import url

from . import views

# Temporary?
from django.views.generic import TemplateView

app_name = 'schedules'
urlpatterns = [
    url(r'^staphers/$', views.StapherList.as_view(), name='staphers-list'),
    url(r'^staphers/create/$', views.StapherCreate.as_view(), name='stapher-create'),
    url(r'^staphers/(?P<pk>[\w-]+)/$', views.StapherDetail.as_view(), name='stapher-detail'),
    url(r'^staphers/(?P<pk>[\w-]+)/edit$', views.StapherUpdate.as_view(), name='stapher-update'),
    url(r'^staphers/(?P<pk>[\w-]+)/delete$', views.StapherDelete.as_view(), name='stapher-delete'),
    url(r'^shifts/$', views.Shift.as_view(), name='shifts'),
]