import datetime

from django.urls import reverse
from dateutil.parser import parse
from operator import attrgetter

from .analytics import get_hours_from_timedelta, get_readable_time, get_td_from_time
from .models import Staphing, Shift, Stapher

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
		if ratio > max_ratio:
			max_ratio = ratio
	return max_ratio


def get_window_during_time(day, time, ratios):
	if day in ratios:
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

def get_q_set_table(q_titles, ratio, largest_needed, shift_link_str):
	cells = []
	num = ratio[0]
	denom = ratio[1]
	if num == denom:
		clean_cell = {}
		clean_cell['color'] = 'yellow'
		cells.append(clean_cell)
	else:
		needed_cell = {}
		availible_cell = {}
		if num < denom:
			needed_cell['color'] = 'green'
			availible_cell['color'] = 'grey'
			for i in range(0, num):
				cells.append(needed_cell)
			for i in range(0, (denom - num)):
				cells.append(availible_cell)
		else:
			needed_cell['color'] = 'red'
			availible_cell['color'] = 'dark_red'
			for i in range(0, denom):
				cells.append(availible_cell)
			for i in range(0, (num - denom)):
				cells.append(needed_cell)
	while len(cells) < largest_needed:
		cells.append(False)
	qual_str = ''
	for i, title in enumerate(q_titles):
		if i > 0:
			string = ', and ' + title if (i + 1) == len(q_titles) else ', ' + title
			qual_str += string				
		else:
			qual_str += title
	table = {}
	table['cells'] = cells
	table['qual_str'] = qual_str if qual_str else 'no'
	table['ratio_msg'] = f'{num} stapher(s) needed. {denom} stapher(s) free and qualified.'
	table['shift_link'] = shift_link_str
	return table


def get_largest_needed(ratio_info):
	largest_needed = 0
	for info in ratio_info:
		ratio = info[0]
		num = ratio[0]
		denom = ratio[1]
		if num > largest_needed:
			largest_needed = num
		if denom > largest_needed:
			largest_needed = denom
	return largest_needed

def get_stapher_table(groups):
	largest_group = 0
	for g in groups:
		if len(g) > largest_group:
			largest_group = len(g)
	all_rows =[[{'header':'Not Free or Qualified'}, {'header':'Not Qualified'},{'header':'Not Free'}, {'header':'Free & Qualified'}]]
	for i in range(0, largest_group):
		new_row = []
		for j, g in enumerate(groups):
			cell = {}
			if i < len(g):
				cell['stapher'] = g[i]
				if j == 3:
					link = reverse('schedules:stapher-schedule-shifts', kwargs={'pk': g[i].id})
				elif j == 2:
					link = reverse('schedules:stapher-schedule', kwargs={'pk': g[i].id})
				elif j == 1:
					link = reverse('schedules:stapher-update', kwargs={'pk': g[i].id})
				else:
					link =  g[i].get_absolute_url() 
				cell['link'] = link
				new_row.append(cell)
			else:
				new_row.append(cell)
		all_rows.append(new_row)
	return all_rows


def get_ratio_tables_in_window(ratios, day, start, end):
	window = get_window_during_time(day, get_td_from_time(start), ratios)
	all_tables = []
	if window:
		ratio_info = window[1]
		largest_needed = get_largest_needed(ratio_info)
		for info in ratio_info:
			q_set_ratio = info[0]
			q_strings = info[1]
			staph_groups = info[2]
			days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday','Saturday']
			link_str = 'uncovered,' + days[day] + ',' + start.strftime("%I:%M %p").lstrip('0').lower()
			for q in q_strings:
				link_str += ', *q ' + q
			q_set_table = get_q_set_table(q_strings, q_set_ratio, largest_needed, link_str)
			stapher_table = get_stapher_table(staph_groups)
			tables = {'qual_table':q_set_table, 'stapher_table': stapher_table}
			all_tables.append(tables)
	return all_tables

def get_stapher_breakdown_table(shift, staphers, staphings):
	availible_workers = []
	not_free_workers = []
	not_qualified_workers = []
	not_free_or_qualified_workers = []
	for stapher in sorted(staphers, key = attrgetter('first_name', 'last_name')):
		stapher_is_qualified = stapher.is_qualified(shift)
		stapher_is_free = stapher.is_free(staphings, shift)
		if stapher_is_qualified:
			if stapher_is_free:
				availible_workers.append(stapher)
			else:
				not_free_workers.append(stapher)
		else:
			if stapher_is_free:
				not_qualified_workers.append(stapher)
			else:
				not_free_or_qualified_workers.append(stapher)
	groups = [not_free_or_qualified_workers, not_qualified_workers, not_free_workers, availible_workers]
	return get_stapher_table(groups)


def get_time_from_string(time_string):
	try:
		print('here')
		if ':' in time_string or 'am' in time_string or 'pm' in time_string:
			string_dt = parse(time_string)
			time = datetime.time(string_dt.hour, string_dt.minute, 0, 0)
		else:
			raise Exception
	except:
		time =  None
	return time

