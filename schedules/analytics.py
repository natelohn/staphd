import datetime

def get_hours_from_timedelta(time_delta):
	return (time_delta.days * 24) + round(time_delta.seconds / 3600, 2)

def get_hours_between_times(start, end):
	start_td = datetime.timedelta(hours = start.hour, minutes = start.minute)
	end_td = datetime.timedelta(hours = end.hour, minutes = end.minute)
	return get_hours_from_timedelta(end_td - start_td)

def get_readable_time(time):
	return time.strftime("%I:%M%p").replace(':00','').lstrip('0').lower()

def get_str_from_td(td):
	hours = td.seconds//3600
	minutes = (td.seconds//60)%60
	return datetime.time(hour = hours, minute = minutes).strftime("%I:%M %p").lstrip('0')

def get_hours_info(stapher, staphers, staphings, shifts_by_day, flags, qualifications):
	off_day = stapher.get_off_day()
	hours_for_days = []
	max_hours = 0
	least_hours = 24
	length_strs = []
	shortest_length = 24
	max_length = 0
	for day in range(0, 7):
		td = stapher.hours_in_day(staphings, day)
		hours = get_hours_from_timedelta(td)
		hours_for_days.append(hours)
		if hours > max_hours:
			max_hours = hours
		if day != off_day and day != off_day - 1:
			if hours < least_hours:
				least_hours = hours	
			shifts = shifts_by_day[day]
			first_shift = shifts[0]
			last_shift = shifts[-1]
			length_str = f'{get_readable_time(first_shift.start)} to {get_readable_time(last_shift.end)}'
			length = get_hours_between_times(first_shift.start, last_shift.end)
			if length < shortest_length:
				shortest_length = length
			if length > max_length:
				max_length = length
		else:
			length_str = 'Off Day'
		length_strs.append(length_str)
	return [sum(hours_for_days)] + hours_for_days + [max_hours, least_hours] + length_strs + [shortest_length, max_length]


def get_average_first_last_info(stapher, staphers, staphings, shifts_by_day, flags, qualifications):
	off_day = stapher.get_off_day()
	total_first_shift_time =  datetime.timedelta(0, 0)
	total_first_shift_time_mid =  datetime.timedelta(0, 0)
	total_last_shift_time = datetime.timedelta(0, 0)
	total_last_shift_time_mid = datetime.timedelta(0, 0)
	for day in range(0, 7):
		if day != off_day:
			shifts = shifts_by_day[day]
			first_shift = shifts[0]
			total_first_shift_time += datetime.timedelta(hours = first_shift.start.hour, minutes = first_shift.start.minute)
			if day in range(2, 5):
				total_first_shift_time_mid += datetime.timedelta(hours = first_shift.start.hour, minutes = first_shift.start.minute)
			if day != off_day - 1: 
				last_shift = shifts[-1]
				total_last_shift_time += datetime.timedelta(hours = last_shift.end.hour, minutes = last_shift.end.minute)
				if day in range(2, 5):
					total_last_shift_time_mid += datetime.timedelta(hours = first_shift.start.hour, minutes = first_shift.start.minute)
	avg_first_shift = get_str_from_td(total_first_shift_time / 6)
	avg_last_shift = get_str_from_td(total_last_shift_time / 5)
	avg_first_shift_mid = get_str_from_td(total_first_shift_time_mid / len(set([2, 3, 4]) - set([off_day])))
	avg_last_shift_mid = get_str_from_td(total_last_shift_time / len(set([2, 3, 4]) - set([off_day - 1, off_day])))
	return [avg_first_shift, avg_last_shift, avg_first_shift_mid, avg_last_shift_mid]

def get_sleep_windows_info(stapher, staphers, staphings, shifts_by_day, flags, qualifications):
	full_day = datetime.timedelta(hours = 24, minutes = 0)
	off_day = stapher.get_off_day()
	days = [1, 2, 3, 4, 5, 6, 0]
	last_shift_of_yesterday = shifts_by_day[0][-1]
	sleep_windows = []
	window_totals = 0
	for day in days:
		if day != off_day:
			shifts = shifts_by_day[day]
			first_shift_of_today = shifts[0]
			morning_td = datetime.timedelta(hours = first_shift_of_today.start.hour, minutes = first_shift_of_today.start.hour)
			night_td = datetime.timedelta(hours = last_shift_of_yesterday.end.hour, minutes = last_shift_of_yesterday.end.hour)
			window = get_hours_from_timedelta((full_day - night_td) + morning_td)
			sleep_windows.append(window)
			window_totals += window
			last_shift_of_yesterday = shifts[-1]
		else:
			sleep_windows.append('Off Day')
	sleep_windows_avg = round(window_totals / 6, 2)
	return sleep_windows + [sleep_windows_avg]



def get_sleep_windows_for_days(stapher, staphers, staphings, shifts_by_day, flags, qualifications):
	full_day = datetime.timedelta(hours = 24, minutes = 0)
	off_day = stapher.get_off_day()
	days = [1, 2, 3, 4, 5, 6, 0]
	last_shift_of_yesterday = shifts_by_day[0][-1]
	sleep_windows = []
	for day in days:
		if day != off_day:
			shifts = shifts_by_day[day]
			first_shift_of_today = shifts[0]
			morning_td = datetime.timedelta(hours = first_shift_of_today.start.hour, minutes = first_shift_of_today.start.hour)
			night_td = datetime.timedelta(hours = last_shift_of_yesterday.end.hour, minutes = last_shift_of_yesterday.end.hour)
			window = get_hours_from_timedelta((full_day - night_td) + morning_td)
			sleep_windows.append(window)
			# Bump the last shift forward
			last_shift_of_yesterday = shifts[-1]
		else:
			sleep_windows.append('Off Day')
	return sleep_windows

def get_avg_sleep_window(stapher, staphers, staphings, shifts_by_day, flags, qualifications):
	full_day = datetime.timedelta(hours = 24, minutes = 0)
	off_day = stapher.get_off_day()
	days = [1, 2, 3, 4, 5, 6, 0]
	last_shift_of_yesterday = shifts_by_day[0][-1]
	sleep_windows_total = 0
	for day in days:
		if day != off_day:
			shifts = shifts_by_day[day]
			first_shift_of_today = shifts[0]
			morning_td = datetime.timedelta(hours = first_shift_of_today.start.hour, minutes = first_shift_of_today.start.hour)
			night_td = datetime.timedelta(hours = last_shift_of_yesterday.end.hour, minutes = last_shift_of_yesterday.end.hour)
			sleep_windows_total += get_hours_from_timedelta((full_day - night_td) + morning_td)
			last_shift_of_yesterday = shifts[-1]
	sleep_windows_avg = round(sleep_windows_total / 6, 2)
	return [sleep_windows_avg]

def get_people_not_worked_with(stapher, staphers, staphings, shifts_by_day, flags, qualifications):
	my_shifts = []
	for staphing in staphings:
		if staphing.stapher.id == stapher.id:
			my_shifts.append(staphing.shift)
	staphers_worked_with = set([stapher])
	for staphing in staphings:
		if staphing.shift in my_shifts and staphing.stapher.id != stapher.id:
			staphers_worked_with.add(staphing.stapher)
	people_not_worked_with = set(staphers) - staphers_worked_with
	not_worked_with_str = ''
	for person in people_not_worked_with:
		not_worked_with_str += person.full_name() + ', '
	if people_not_worked_with:
		not_worked_with_str = not_worked_with_str[:-2]
	return [len(people_not_worked_with), not_worked_with_str]

def get_total_day_off_time(stapher, staphers, staphings, shifts_by_day, flags, qualifications):
	off_day = stapher.get_off_day()
	last_shift_before_off_day = shifts_by_day[off_day - 1][-2]
	first_shift_after_off_day = shifts_by_day[off_day + 1][0]
	off_time_before = 24 - get_hours_between_times(datetime.time.min, last_shift_before_off_day.end)
	off_time_after = get_hours_between_times(datetime.time.min, first_shift_after_off_day.start)
	return [off_time_before + 24 + off_time_after]

# TODO: Apply this analytic
def get_special_shift_success_rate(stapher, staphers, staphings, shifts_by_day, flags, qualifications):
	return ['Not Yet Applied', 'Not Yet Applied']

def get_average_window_between_shifts(stapher, staphers, staphings, shifts_by_day, flags, qualifications):
	window_sizes = []
	for day in range(0, 7):
		shifts = shifts_by_day[day]
		# Only want to count non-off-day shifts
		if len(shifts) > 1:
			for i in range(1, len(shifts)):
				last_shift = shifts[i - 1]
				next_shift = shifts[i]
				window_size = get_hours_between_times(last_shift.end, next_shift.start)
				if window_size:
					window_sizes.append(window_size)
	avg = round(sum(window_sizes) / len(window_sizes), 2)
	return [avg]

def get_flag_information(stapher, staphers, staphings, shifts_by_day, flags, qualifications):
	flag_ids_to_hours = {}
	for flag in flags:
		flag_ids_to_hours[flag.id] = 0
	for day in shifts_by_day:
		for shift in shifts_by_day[day]:
			for flag in shift.flags.all():
				if flag.id in flag_ids_to_hours:
					flag_ids_to_hours[flag.id] += get_hours_from_timedelta(shift.length())
	return [flag_ids_to_hours[flag.id] for flag in flags]

def get_qualification_information(stapher, staphers, staphings, shifts_by_day, flags, qualifications):
	qual_ids_to_hours = {}
	for qual in qualifications:
		qual_ids_to_hours[qual.id] = 0
	for day in shifts_by_day:
		for shift in shifts_by_day[day]:
			for qual in shift.qualifications.all():
				if qual.id in qual_ids_to_hours:
					qual_ids_to_hours[qual.id] += get_hours_from_timedelta(shift.length())
	return [qual_ids_to_hours[qual.id] for qual in qualifications]

def get_analytics(staphers, staphings, flags, qualifications):
	print('Generating Analytics...')
	initial_row = [
		'Name',
		'Total Hours',
		'Hours on Sunday',
		'Hours on Monday',
		'Hours on Tuesday',
		'Hours on Wednesday',
		'Hours on Thursday',
		'Hours on Friday',
		'Hours on Saturday',
		'Most Hours in Day',
		'Least Hours in Day',
		'Sunday\'s Start to End',
		'Tuesday\'s Start to End',
		'Monday\'s Start to End',
		'Wednesday\'s Start to End',
		'Thursday\'s Start to End',
		'Friday\'s Start to End',
		'Saturday\'s Start to End',
		'Shortest Day (First to Last Shift)',
		'Longest Day (First to Last Shift)',
		'Average Time First Shift Starts',
		'Average Time Last Shift Ends',
		'Average Time First Shift Starts (Tues-Thur)',
		'Average Time Last Shift Ends (Tue-Thur)',
		'Hours of Sleep (Sun-Mon)',
		'Hours of Sleep (Mon-Tue)',
		'Hours of Sleep (Tue-Wed)',
		'Hours of Sleep (Wed-Thu)',
		'Hours of Sleep (Thu-Fri)',
		'Hours of Sleep (Fri-Sat)',
		'Hours of Sleep (Sat-Sun)',
		'Average Hours of Sleep',
		'# of People You\'re Not Scheduled With',
		'People You\'re Not Scheduled With',
		'Total Time of Off Day',
		'# of Top 3 Special Shifts on Schedule',
		'# of Top 5 Special Shifts on Schedule',
		'Average Hours Between Shifts',
	]
	for flag in flags:
		initial_row.append(f'Hours with {flag} flag.')
	for qual in qualifications:
		initial_row.append(f'Hours with {qual} qualification.')
	analytics = [initial_row]
	funtions = [
		get_hours_info,
		get_average_first_last_info,
		get_sleep_windows_info,
		get_people_not_worked_with,
		get_total_day_off_time,
		get_special_shift_success_rate,
		get_average_window_between_shifts,
		get_flag_information,
		get_qualification_information
	]
	for stapher in staphers:
		print(f'Updating analytics for {stapher.full_name()}...')
		stapher_analytics = [stapher.full_name()]
		shifts_by_day = stapher.shifts_by_day(staphings)
		for function in funtions:
			stapher_analytics.extend(function(stapher, staphers, staphings, shifts_by_day, flags, qualifications))
		analytics.append(stapher_analytics)
	return analytics

