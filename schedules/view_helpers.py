from .analytics import get_hours_from_timedelta, get_readable_time


def get_week_schedule_view_info(stapher, staphings):
	days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday','Saturday']
	time = datetime.timedelta(hours = 6, minutes = 0)
	max_time = datetime.timedelta(hours = 23, minutes = 30)
	increment = datetime.timedelta(hours = 0, minutes = 15)
	all_rows_for_time = [days]
	seen_shifts = set()
	while time <= max_time:
		hours = int(get_hours_from_timedelta(time))
		minutes = (time.seconds//60)%60
		t = datetime.time(hours, minutes, 0, 0)
		row_for_time = []
		for i, day in enumerate(days):
			shift = stapher.get_shift_during_time(i, t, staphings)
			if not shift:
				row_for_time.append(False)
			elif shift.id not in seen_shifts:
				cell = {}
				cell['title'] = f'{shift.title}, {get_readable_time(shift.start)}-{get_readable_time(shift.end)}'
				cell['span'] = get_hours_from_timedelta(shift.length()) * 4
				row_for_time.append(cell)
				seen_shifts.add(shift.id)
				
		all_rows_for_time.append(row_for_time)
		time += increment
	return all_rows_for_time