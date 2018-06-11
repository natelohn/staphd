import datetime

from .analytics import get_hours_from_timedelta, get_readable_time, get_td_from_time
from .models import Staphing, Shift

def get_min(time):
	m = time.minute / 60
	min_options = [0, 0.25, 0.33, 0.5, 0.66, 0.75, 1]
	for i, opt in enumerate(min_options):
		if min_options[i] <= m and m < min_options[i + 1]:
			return min_options[i]

def get_time_str(time):
	h = time.hour
	m = get_min(time)
	return str(h + m)

def get_shift_csv(shift):
	csv = ''
	for flag in shift.flags.all():
		csv += flag.title + ','
	csv += str(shift.day) + ',' + shift.title + ',' + get_time_str(shift.start) + ',' + get_time_str(shift.end) + ',' + str(shift.workers_needed) + ','
	for qual in shift.qualifications.all():
		csv += qual.title + ','
	return csv[:-1]

def make_shifts_csv(schedule):
	all_csv_strings = []
	for shift in Shift.objects.filter(shift_set = schedule.shift_set):
		csv_string = get_shift_csv(shift)
		all_csv_strings.append(csv_string)
	return all_csv_strings

def make_staphings_csv(schedule):
	all_csv_strings = []
	all_staphings = Staphing.objects.filter(schedule_id__exact = schedule.id)
	for staphing in all_staphings:
		shift_csv = get_shift_csv(staphing.shift)
		csv_string = staphing.stapher.full_name() + ',' + shift_csv
		all_csv_strings.append(csv_string)
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


def get_span_from_time(start, end):
	start_td = get_td_from_time(start)
	end_td = get_td_from_time(end)
	length = end_td - start_td
	row_span = ((length.seconds / 60) / 5)
	return int(row_span)

def get_max_ratio(ratios):
	max_ratio = 0
	for info in ratios:
		r = info[0]
		num = r[0]
		denom = r[1]
		ratio = (num / denom) if denom else num + 1
		print(f'{num}/{denom} = {ratio}')

		print(f'{info[1]}')
		li = ['! f or q', '! qual', '! free', 'Free and Qualified']
		for i, s_set in enumerate(info[2]):
			print(f'{len(s_set)} staphers {li[i]}:')
			for s in s_set:
				print(f'	- {s}')
		print('=--------------=---------=-------=----------')
		if ratio > max_ratio:
			max_ratio = ratio

	return max_ratio


def get_window_during_time(day, time, ratios):
	for r in ratios[day]:
		time_info = r[0]
		start_td = get_td_from_time(time_info[0])
		end_td = get_td_from_time(time_info[1])
		if start_td <= time and time < end_td:
			return r
	return None


def get_ratio_table(ratios):
	days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday','Saturday']
	time = datetime.timedelta(hours = 6, minutes = 0)
	max_time = datetime.timedelta(hours = 23, minutes = 30)
	increment = datetime.timedelta(hours = 0, minutes = 5)
	all_rows_for_time = [days]
	seen_windows = {}
	for day in range(0, 7):
		seen_windows[day] = []
	while time <= max_time:
		row_for_time = []
		for day in range(0, 7):
			window = get_window_during_time(day, time, ratios)

			if not window:
				row_for_time.append(False)
			else:
				time_info = window[0]
				start = time_info[0]
				end = time_info[1]
				ratio_info = window[1]
				if start not in seen_windows[day]:
					cell = {}
					start_txt = get_readable_time(start)
					end_txt = get_readable_time(end)
					cell['title'] = f'{start_txt}-{end_txt}'
					cell['span'] = get_span_from_time(start, end)
					cell['max_ratio'] = get_max_ratio(ratio_info)
					cell['day'] = day
					cell['s_url'] = start.strftime("%H%M")
					cell['e_url'] = end.strftime("%H%M")
					row_for_time.append(cell)
					seen_windows[day].append(start)
				
		all_rows_for_time.append(row_for_time)
		time += increment
	return all_rows_for_time






