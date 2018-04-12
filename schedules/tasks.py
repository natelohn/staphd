from __future__ import absolute_import
from celery import shared_task, current_task
from django.db.models.functions import Lower
from staphd.celery import app
import time

from .excel import update_individual_excel_files, update_masters, update_analytics
from .models import Flag, Stapher, Staphing, Qualification, Master



@app.task(bind=True, track_started=True)
@shared_task(bind=True)
def update_files_task(self, schedule_id):
	test_wait_secs = 2
	total_wait_secs = test_wait_secs * 3
	staphings = Staphing.objects.filter(schedule__id = schedule_id)
	all_masters = Master.objects.all()
	all_staphers = Stapher.objects.all().order_by(Lower('first_name'), Lower('last_name'))
	all_flags = Flag.objects.all().order_by(Lower('title'))
	all_qualifications = Qualification.objects.all().order_by(Lower('title'))
	curr_percent = 1
	for i in range(0, test_wait_secs):
		percent = int(100 * float(curr_percent) / float(total_wait_secs))
		current_task.update_state(meta = {'message':'Making Excels', 'process_percent':percent})
		time.sleep(1)
		curr_percent += 1
		print(f'...Making Excels - {percent}%')
		
	# update_individual_excel_files(all_staphers, staphings)
	for i in range(0, test_wait_secs):
		percent = int(100 * float(curr_percent) / float(total_wait_secs))
		current_task.update_state(meta = {'message':'Making Masters', 'process_percent':percent})
		time.sleep(1)
		curr_percent += 1
		print(f'...Making Masters - {percent}%')
		
	# update_masters(all_masters, staphings)
	for i in range(0, test_wait_secs):
		percent = int(100 * float(curr_percent) / float(total_wait_secs))
		current_task.update_state(meta = {'message':'Making Analytics', 'process_percent':percent})
		time.sleep(1)
		curr_percent += 1
		print(f'...Making Analytics - {percent}%')
	# update_analytics(all_staphers, staphings, all_flags, all_qualifications)

