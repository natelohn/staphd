from django.conf.urls import url

from . import views

app_name = 'schedules'
urlpatterns = [

    url(r'^$', views.build_view, name='home'),
    url(r'^schedules/$', views.build_view, name='schedule'),
    url(r'^schedules/settings/select$', views.SettingParameterUpdate.as_view(), name='settings-select'),
    url(r'^schedules/settings/rank/$', views.rank_settings, name='settings-rank'),
    url(r'^schedules/settings/rank/up/(?P<pk>[\d]+)$', views.rank_up, name='rank-up'),
    url(r'^schedules/settings/rank/down/(?P<pk>[\d]+)$', views.rank_down, name='rank-down'),
    url(r'^schedules/settings/auto$', views.SettingPreferenceUpdate.as_view(), name='settings-auto'),
    url(r'^schedules/select/$', views.ScheduleList.as_view(), name='select'),
    url(r'^schedules/select/(?P<pk>[\d]+)$', views.schedule_selected, name='schedule-selected'),
    url(r'^schedules/create$', views.ScheduleCreate.as_view(), name='schedule-create'),
    url(r'^schedules/duplicate/(?P<pk>[\d]+)$', views.schedule_duplicate, name='duplicate'),
    url(r'^schedules/update$', views.update_files, name='update'),
    url(r'^schedules/building$', views.build_schedules, name='building'),
    url(r'^schedules/track$', views.track_state, name='track'),
    url(r'^schedules/redirect$', views.redirect, name='redirect'),
    url(r'^schedules/recommendation$', views.recommendations_view, name='recommendation'),
    url(r'^schedules/recommendation/add/(?P<pk>[\d]+)$', views.add_recommendation, name='recommendation_add'),
    url(r'^schedules/(?P<pk>[\d]+)/$', views.ScheduleDetail.as_view(), name='schedule-detail'),
    url(r'^schedules/(?P<pk>[\d]+)/delete$', views.ScheduleDelete.as_view(), name='schedule-delete'),
    url(r'^schedules/(?P<pk>[\d]+)/edit$', views.ScheduleUpdate.as_view(), name='schedule-update'),
    url(r'^schedules/get_ratios$', views.get_ratio, name='get-ratio'),
    url(r'^schedules/ratios/$', views.ratio_week_view, name='ratio-week'),
    url(r'^schedules/ratios/(?P<d>[\d]+)/(?P<s>[\d]+)/(?P<e>[\d]+)/$', views.ratio_window_view, name='ratio-window'),
    url(r'^schedules/special/$', views.rank_staphers_view, name='special'),
    url(r'^schedules/special/(?P<pk>[\d]+)/up$', views.rank_staphers_up, name='special-rank-up'),
    url(r'^schedules/special/(?P<pk>[\d]+)/down$', views.rank_staphers_down, name='special-rank-down'),
    url(r'^schedules/special/placement$', views.place_special_shifts, name='special-placement'),
    url(r'^schedules/special/results$', views.special_shifts_results, name='special-results'),

    url(r'^download/$', views.DownloadView.as_view(), name='download'),
    url(r'^download/individual$', views.download_individual, name='download-individual'),
    url(r'^download/masters$', views.download_masters, name='download-masters'),
    url(r'^download/meals$', views.download_meals, name='download-meals'),
    url(r'^download/analytics$', views.download_analytics, name='download-analytics'),

    url(r'^flag/create$', views.FlagCreate.as_view(), name='flag-create'),
    url(r'^flag/(?P<pk>[\d]+)/delete$', views.FlagDelete.as_view(), name='flag-delete'),

    url(r'^extras/$', views.Settings.as_view(), name='settings'),
    url(r'^extras/flags$', views.FlagSettings.as_view(), name='flag-settings'),
    url(r'^extras/qualifications$', views.QualificationSettings.as_view(), name='qualification-settings'),
    url(r'^extras/sets$', views.ShiftSetList.as_view(), name='shift-set-list'),

    url(r'^shifts/$', views.ShiftList.as_view(), name='shift-list'),
    url(r'^shifts/create$', views.ShiftCreate.as_view(), name='shift-create'),
    url(r'^shifts/(?P<pk>[\d]+)$', views.ShiftDetail.as_view(), name='shift-detail'),
    url(r'^shifts/(?P<pk>[\d]+)/edit$', views.ShiftUpdate.as_view(), name='shift-update'),
    url(r'^shifts/(?P<pk>[\d]+)/delete$', views.ShiftDelete.as_view(), name='shift-delete'),
    url(r'^shifts/(?P<sort>[\D]*)/(?P<key>[\d]*)$', views.ShiftList.as_view(), name='shift-list-sort'),

    url(r'^staphers/$', views.StapherList.as_view(), name='stapher-list'),
    url(r'^staphers/create$', views.StapherCreate.as_view(), name='stapher-create'),
    url(r'^staphers/(?P<pk>[\d]+)/$', views.StapherDetail.as_view(), name='stapher-detail'),
    url(r'^staphers/(?P<pk>[\d]+)/edit$', views.StapherUpdate.as_view(), name='stapher-update'),
    url(r'^staphers/(?P<pk>[\d]+)/delete$', views.StapherDelete.as_view(), name='stapher-delete'),
    url(r'^staphers/(?P<pk>[\d]+)/schedule/$', views.stapher_schedule_view, name='stapher-schedule'),
    url(r'^staphers/(?P<pk>[\d]+)/schedule/add$', views.stapher_schedule_add, name='stapher-schedule-shifts'),
    url(r'^staphers/(?P<pk>[\d]+)/schedule/add/(?P<s>[\d]+)$', views.stapher_shift_scheduled, name='stapher-shift-scheduled'),
    url(r'^staphers/(?P<pk>[\d]+)/cover/$', views.stapher_cover, name='stapher-cover'),
    url(r'^staphers/preferences/(?P<pk>[\d]+)/$', views.stapher_preferences, name='stapher-preferences'),
    url(r'^staphers/preferences/(?P<pk>[\d]+)/up$', views.stapher_preferences_up, name='stapher-preferences-up'),
    url(r'^staphers/preferences/(?P<pk>[\d]+)/down$', views.stapher_preferences_down, name='stapher-preferences-down'),
    url(r'^staphers/preferences/(?P<pk>[\d]+)/(?P<f>[\d]+)$', views.stapher_preferences_add, name='stapher-preferences-add'),
    url(r'^staphers/preferences/delete/(?P<pk>[\d]+)$', views.stapher_preferences_delete, name='stapher-preferences-delete'),

    url(r'^qualification/create$', views.QualificationCreate.as_view(), name='qualification-create'),
    url(r'^qualification/(?P<pk>[\d]+)/delete$', views.QualificationDelete.as_view(), name='qualification-delete'),

    url(r'^staphing/(?P<pk>[\d]+)/delete$', views.StaphingDelete.as_view(), name='staphing-delete'),

    url(r'^set/create/$', views.ShiftSetCreate.as_view(), name='set-create'),
    url(r'^set/add/(?P<pk>[\d]+)$', views.shift_set_add, name='set-add'),
    url(r'^set/delete/(?P<pk>[\d]+)$', views.ShiftSetDelete.as_view(), name='set-delete'),

]