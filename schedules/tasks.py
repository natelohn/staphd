from __future__ import absolute_import
from celery import shared_task, current_task
from django.core.cache import cache
from django.db.models.functions import Lower
from staphd.celery import app
import time

from .excel import update_individual_excel_files, update_masters, update_analytics
from .models import Flag, Stapher, Staphing, Qualification, Master


@app.task(bind=True, track_started=True)
@shared_task(bind=True)
def update_files_task(self, schedule_id):
	# Get necessary information from the DB
	staphings = Staphing.objects.filter(schedule__id = schedule_id)
	all_masters = Master.objects.all()
	all_staphers = Stapher.objects.all().order_by(Lower('first_name'), Lower('last_name'))
	all_flags = Flag.objects.all().order_by(Lower('title'))
	all_qualifications = Qualification.objects.all().order_by(Lower('title'))

	# Set the amount of actions for the task to recieve later to use for percentage
	num_total_actions = (len(all_staphers) * 2) + ((len(all_masters) * 2) - 3) + 3
	cache.set('num_actions_made', 0, None)
	cache.set('num_total_actions', num_total_actions, None)

	# Do the task
	update_individual_excel_files(all_staphers, staphings)
	update_masters(all_masters, staphings)
	update_analytics(all_staphers, staphings, all_flags, all_qualifications)

	# Delete the amount of actions from the cache
	cache.set('num_actions_made', None, 0)
	cache.set('num_total_actions', None, 0)


@app.task(bind=True, track_started=True)
@shared_task(bind=True)
def build_schedules_task(self, sorted_shifts):
	settings = ScheduleSettings.objects.get()
	schedule = build_schedules(sorted_shifts)
	cache.set('schedule_id', schedule.id, None)







