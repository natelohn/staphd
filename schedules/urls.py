from django.conf.urls import url

from . import views

# Temporary?
from django.views.generic import TemplateView

app_name = 'schedules'
urlpatterns = [
    url(r'^$', views.HomeView.as_view(), name='home'),

    url(r'^download/$', views.DownloadView.as_view(), name='download'),
    url(r'^download/individual$', views.download_individual, name='download-individual'),
    url(r'^download/masters$', views.download_masters, name='download-masters'),
    url(r'^download/meals$', views.download_meals, name='download-meals'),
    url(r'^download/analytics$', views.download_analytics, name='download-analytics'),

    url(r'^flag/create/$', views.FlagCreate.as_view(), name='flag-create'),
    url(r'^flag/(?P<pk>[\d]+)/delete$', views.FlagDelete.as_view(), name='flag-delete'),

    url(r'^schedules/$', views.build_view, name='schedule'),
    url(r'^schedules/building$', views.build_schedules, name='building'),
    url(r'^schedules/update$', views.update_files, name='update'),
    url(r'^schedules/track$', views.track_state, name='track'),
    url(r'^schedules/select$', views.ScheduleList.as_view(), name='select'),
    url(r'^schedules/create$', views.ScheduleCreate.as_view(), name='schedule-create'),

    url(r'^settings/$', views.Settings.as_view(), name='settings'),
    url(r'^settings/flags/$', views.FlagSettings.as_view(), name='flag-settings'),
    url(r'^settings/qualifications/$', views.QualificationSettings.as_view(), name='qualification-settings'),

    url(r'^shifts/$', views.ShiftList.as_view(), name='shift-list'),
    url(r'^shifts/create/$', views.ShiftCreate.as_view(), name='shift-create'),
    url(r'^shifts/(?P<pk>[\d]+)/$', views.ShiftDetail.as_view(), name='shift-detail'),
    url(r'^shifts/(?P<pk>[\d]+)/edit$', views.ShiftUpdate.as_view(), name='shift-update'),
    url(r'^shifts/(?P<pk>[\d]+)/delete$', views.ShiftDelete.as_view(), name='shift-delete'),
    url(r'^shifts/(?P<sort>[\D]*)/(?P<key>[\d]*)$', views.ShiftList.as_view(), name='shift-list-sort'),

    url(r'^staphers/$', views.StapherList.as_view(), name='stapher-list'),
    url(r'^staphers/create/$', views.StapherCreate.as_view(), name='stapher-create'),
    url(r'^staphers/(?P<pk>[\d]+)/$', views.StapherDetail.as_view(), name='stapher-detail'),
    url(r'^staphers/(?P<pk>[\d]+)/edit$', views.StapherUpdate.as_view(), name='stapher-update'),
    url(r'^staphers/(?P<pk>[\d]+)/delete$', views.StapherDelete.as_view(), name='stapher-delete'),

    url(r'^qualification/create/$', views.QualificationCreate.as_view(), name='qualification-create'),
    url(r'^qualification/(?P<pk>[\d]+)/delete$', views.QualificationDelete.as_view(), name='qualification-delete')

]