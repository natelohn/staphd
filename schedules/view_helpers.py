import datetime

from .analytics import get_hours_from_timedelta, get_readable_time


def get_week_schedule_view_info(stapher, staphings):
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
				row_for_time.append(cell)
				seen_staphings.add(staphing.id)
				
		all_rows_for_time.append(row_for_time)
		time += increment
	return all_rows_for_time


def get_shifts_by_day(stapher, shifts, staphings):
	days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday','Saturday']
	shifts_by_day = {}
	for day in days:
		shifts_by_day[day] = []
	for shift in shifts:
		if not shift.is_covered(staphings):
			if stapher.can_cover(shift, staphings):
				shifts_by_day[days[shift.day]].append(shift)
	return shifts_by_day