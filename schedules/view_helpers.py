import datetime

from .analytics import get_hours_from_timedelta, get_readable_time
from .models import Staphing, Shift

def get_min(time):
	m = round(time.min / 60, 2)
	min_options = [0, 0.25, 0.33, 0.5, 0.66, 0.75, 1]
	if m not in min_options:
		for i, opt in enumerate(min_options):
			if min_options[i] < m and m < min_options[i + 1]:
				return min_options[i]

def get_time_str(time):
	h = time.hour
	m = get_min(time)
	return str(h + m)

def get_shift_csv(shift):
	csv = ''
	for flag in shift.flags.all():
		csv += flag.title + ','
	info_str = str(shift.day) + ',' + shift.title + ',' + get_time_str(shift.start) + ',' + get_time_str(shift.end) + ',' + str(shift.workers_needed) + ','
	csv += info_str 
	for qual in shift.qualifications.all():
		csv += qual.title + ','
	return csv[:-1]

def make_shifts_csv():
	all_csv_strings = []
	for shift in Shift.objects.all():
		csv_string = get_shift_csv(shift)
		all_csv_strings.append(csv_string)
		print(f'csv_string = {csv_string}')
	return all_csv_strings


def get_week_schedule_view_info(stapher, staphings, shift, schedule):
	if shift:
		new_staphings = Staphing(stapher = stapher, shift = shift, schedule = schedule)
		staphings = list(staphings)
		staphings.append(new_staphings)
	days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday','Saturday']
	time = datetime.timedelta(hours = 6, minutes = 0)
	max_time = datetime.timedelta(hours = 23, minutes = 30)
	increment = datetime.timedelta(hours = 0, minutes = 15)
	all_rows_for_time = [days]
	seen_staphings = set()
	while time <= max_time:
		hours = int(get_hours_from_timedelta(time))
		minutes = (time.seconds//60)%60
		t = datetime.time(hours, minutes, 0, 0)
		row_for_time = []
		for i, day in enumerate(days):
			staphing = stapher.get_staphing_during_time(i, t, staphings)
			if not staphing:
				row_for_time.append(False)
			elif staphing.id not in seen_staphings:
				cell = {}
				cell['title'] = f'{staphing.shift.title}, {get_readable_time(staphing.shift.start)}-{get_readable_time(staphing.shift.end)}'
				cell['span'] = get_hours_from_timedelta(staphing.shift.length()) * 4
				cell['staphing_id'] = staphing.id
				cell['shift'] = staphing.shift
				if shift:
					cell['new_shift'] = staphing.shift.id == shift.id
				row_for_time.append(cell)
				seen_staphings.add(staphing.id)
				
		all_rows_for_time.append(row_for_time)
		time += increment
	return all_rows_for_time


def get_shifts_to_add(stapher, shifts, all_staphings, stapher_staphings):
	shifts_by_day = {0:[], 1:[], 2:[], 3:[], 4:[], 5:[], 6:[]}
	most_shifts_in_day = 0
	for shift in shifts:
		if stapher.can_cover(shift, stapher_staphings):
			if not shift.is_covered(all_staphings):
				shifts_by_day[shift.day].append(shift)
				if len(shifts_by_day[shift.day]) > most_shifts_in_day:
					most_shifts_in_day = len(shifts_by_day[shift.day])

	days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday','Saturday']
	all_rows = [days]
	for i in range(0, most_shifts_in_day):
		new_row = []
		for day, string in enumerate(days):
			if i < len(shifts_by_day[day]):
				shift = shifts_by_day[day][i]
				time_string = f'{get_readable_time(shift.start)}-{get_readable_time(shift.end)}'
				cell = {'shift':shift, 'time_string':time_string}
				new_row.append(cell)
			else:
				new_row.append('')
		all_rows.append(new_row)
	return all_rows