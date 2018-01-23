from django.conf.urls import url

from . import views

# Temporary?
from django.views.generic import TemplateView

app_name = 'schedules'
urlpatterns = [
    url(r'^staphers/$', views.StapherList.as_view(), name='stapher-list'),
    url(r'^staphers/create/$', views.StapherCreate.as_view(), name='stapher-create'),
    url(r'^staphers/(?P<pk>[\w-]+)/$', views.StapherDetail.as_view(), name='stapher-detail'),
    url(r'^staphers/(?P<pk>[\w-]+)/edit$', views.StapherUpdate.as_view(), name='stapher-update'),
    url(r'^staphers/(?P<pk>[\w-]+)/delete$', views.StapherDelete.as_view(), name='stapher-delete'),
    url(r'^shifts/$', views.ShiftList.as_view(), name='shift-list'),
    url(r'^shifts/create/$', views.ShiftCreate.as_view(), name='shift-create'),
    url(r'^shifts/(?P<pk>[\w-]+)/$', views.ShiftDetail.as_view(), name='shift-detail'),
    url(r'^shifts/(?P<pk>[\w-]+)/edit$', views.ShiftUpdate.as_view(), name='shift-update'),
    url(r'^shifts/(?P<pk>[\w-]+)/delete$', views.ShiftDelete.as_view(), name='shift-delete'),
    url(r'^qualification/create/$', views.QualificationCreate.as_view(), name='qualification-create'),
    url(r'^qualification/(?P<pk>[\w-]+)/delete$', views.QualificationDelete.as_view(), name='qualification-delete'),
    url(r'^flag/create/$', views.FlagCreate.as_view(), name='flag-create'),
    url(r'^flag/(?P<pk>[\w-]+)/delete$', views.FlagDelete.as_view(), name='flag-delete'),
]