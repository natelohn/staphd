import datetime


def get_scheduled_hours_in_shifts_day(stapher, shift, staphings, all_shifts):
	return stapher.hours_in_day(staphings, shift.day)

def get_total_scheduled_hours_in_schedule(stapher, shift, staphings, all_shifts):
	return stapher.total_hours(staphings)

def get_number_of_shifts_with_any_matching_flags(stapher, shift, staphings, all_shifts):
	count_of_any_matching_flags = 0
	for staphing in staphings:
		if stapher == staphing.stapher and shift.has_matching_flags(staphing.shift):
			count_of_any_matching_flags += 1
	return count_of_any_matching_flags

def get_number_of_shifts_with_all_matching_flags(stapher, shift, staphings, all_shifts):
	count_of_all_matching_flags = 0
	for staphing in staphings:
		if stapher == staphing.stapher and shift.has_exact_flags(staphing.shift):
			count_of_all_matching_flags += 1
	return count_of_all_matching_flags

# Return the size of the length of time from the end of the shift before the given shift 
# 	and the start of the shift after the given shift.
def get_time_between_last_and_next_shift(stapher, shift, staphings, all_shifts):
	previous_shift = stapher.get_previous_shift(shift, staphings)
	next_shift = stapher.get_next_shift(shift, staphings)

	# If the shift before/after this shift is not on the same day or there is no shift scheduled before/after this one,
	# 	we will keep the time at the earliest/latest possible time in the day.
	start_of_window = datetime.time.min
	end_of_window = datetime.time.max
	if bool(previous_shift) and previous_shift.day == shift.day:
		start_of_window = previous_shift.end

	if bool(next_shift) and next_shift.day == shift.day:
		end_of_window = next_shift.start


	# We then covert the time object to timedelt and return the difference.
	start_td = datetime.timedelta(hours = start_of_window.hour, minutes = start_of_window.minute)
	end_td = datetime.timedelta(hours = end_of_window.hour, minutes = end_of_window.minute)
	return end_td - start_td

def hours_of_difficult_shifts_in_schedule(stapher, shift, staphings, all_shifts):
	difficult_hours = 0
	for staphing in staphings:
		if stapher.id == staphing.stapher.id and staphing.shift.difficult:
			difficult_hours += staphing.shift.length()
	return difficult_hours

def hours_of_difficult_shifts_in_day(stapher, shift, staphings, all_shifts):
	difficult_hours = 0
	for staphing in staphings:
		if stapher.id == staphing.stapher.id and shift.day == staphing.shift.day and staphing.shift.difficult:
			difficult_hours += staphing.shift.length()
	return difficult_hours

def hours_of_difficult_shifts_in_adjacent_days(stapher, shift, staphings, all_shifts):
	difficult_hours = 0
	for staphing in staphings:
		shift_is_adjacent_day = staphing.shift.day == shift.previous_day() or staphing.shift.day == shift.next_day() 
		if stapher.id == staphing.stapher.id and shift_is_adjacent_day and staphing.shift.difficult:
			difficult_hours += staphing.shift.length()
	return difficult_hours

# This function return the difference made in the ammount the person can sleep if the shift is added to their schedule.
# Possible Cases:
	# Case 1: No previous shift, no next shift
	# Case 2: No previous shift, next shift is on or after next day.
	# Case 3: Previous shift is on or before previous day, no next shift.
	# Case 4: Previous shift is on or before previous day, next shift is on or after next day.
		# Cases 1-4 return the change in sleep window change if the person woke up at 10am and went to bed at 8pm
	# Case 5: Previous shift is on same day, next shift is on or after next day.
	# Case 6: Previous shift is on or before previous day, next shift is on same day.
	# Case 7: Previous shift and next shift is on the same day
		# Cases 5-7 set the morning change to 0 if there is a previous shift on the same day (no change to wake up time)
		#	 and the night change to 0 if there is a next shift on the same day (no change to bed time)
def change_in_sleep_window(stapher, shift, staphings, all_shifts):

	start = datetime.timedelta(hours = shift.start.hour, minutes = shift.start.minute)
	end = datetime.timedelta(hours = shift.end.hour, minutes = shift.end.minute)

	# Next we get the shifts before and after the given shift
	previous_shift = stapher.get_previous_shift(shift, staphings)
	next_shift = stapher.get_next_shift(shift, staphings)

	# First we get the default wake/sleep times to use if they have no morning or night shifts scheduled.
	previous_start_td = datetime.timedelta(hours = 10, minutes = 0)
	next_end_td = datetime.timedelta(hours = 20, minutes = 0)

	# If there are previous/next shifts and those shifts are on the same day,
	# 	then set the previous shifts start to whenever 
	if previous_shift:
		# This will set the ammount of morning change to 0 since the previous shift on the same day always ends before the next shift.
		if previous_shift.day == shift.day:
			previous_start_td = datetime.timedelta(hours = previous_shift.start.hour, minutes = previous_shift.start.minute)

	if next_shift:
		# This will set the ammount of night change to 0 since the next shift on the same day always ends after the previous shift.
		if next_shift.day == shift.day:
			next_end_td = datetime.timedelta(hours = next_shift.end.hour, minutes = next_shift.end.minute)
	
	zero_time = datetime.timedelta(hours = 0, minutes = 0)
	morning_change = max(zero_time, previous_start_td - start)
	night_change = max(zero_time, end - next_end_td)
	return morning_change + night_change


# Returns the number of other sifts the stapher could cover in the same time window.
def number_of_other_shifts_stapher_could_cover(stapher, shift, staphings, all_shifts):
	number_of_shifts = 0
	for other_shift in all_shifts:
		if shift.overlaps(other_shift):
			if not other_shift.is_covered(staphings) and stapher.can_cover(other_shift, staphings):
				number_of_shifts += 1
	return number_of_shifts

# Returns the change in ammount of time the person has off if the shift is scheduled.
def get_change_in_off_day_window(stapher, shift, staphings, all_shifts):
	change = datetime.timedelta(hours = 0, minutes = 0)
	off_day = stapher.get_off_day()

	# Set the default end time for the day before your off day to 6am and the default start time for the day after your off day to 11:30pm.
	current_end = datetime.timedelta(hours = 6, minutes = 0)
	current_start = datetime.timedelta(hours = 23, minutes = 30)
	if shift.day == (off_day - 1):
		new_end = datetime.timedelta(hours = shift.end.hour, minutes = shift.end.minute)
		next_shift = stapher.get_next_shift(shift, staphings)
		if next_shift:
			if next_shift.day != shift.day:
				current_end = datetime.timedelta(hours = next_shift.end.hour, minutes = next_shift.end.minute)
		change = new_end - current_end
	elif shift.day == (off_day + 1):
		prev_shift = stapher.get_next_shift(shift, staphings)
		new_start = datetime.timedelta(hours = shift.end.hour, minutes = shift.end.minute)
		prev_shift = stapher.get_previous_shift(shift, staphings)
		if prev_shift:
			if prev_shift.day != shift.day:
				current_start = datetime.timedelta(hours = prev_shift.start.hour, minutes = prev_shift.start.minute)
		change = current_start - new_start
	return change

def increase_in_people_worked_with(stapher, shift, staphings, all_shifts):
	staphers_worked_with = set()
	my_shifts = []
	new_staphers = set()
	for staphing in staphings:
		if staphing.stapher.id == stapher.id:
			my_shifts.append(staphing.shift)
		elif staphing.shift.id == shift.id:
			new_staphers.add(staphing.stapher)
	if new_staphers:
		for staphing in staphings:
			if staphing.shift in my_shifts and staphing.stapher.id != stapher.id:
				staphers_worked_with.add(staphing.stapher)
	return len(new_staphers - staphers_worked_with)

def change_in_average_bedtime(stapher, shift, staphings, all_shifts):
	change = datetime.timedelta(hours = 0, minutes = 0)
	next_shift = stapher.get_next_shift(shift, staphings)
	if not next_shift:
		is_last_shift = True
	else:
		is_last_shift = shift.day != next_shift.day
	if is_last_shift:
		old_ending_shifts = []
		new_ending_shifts = []
		shifts_by_day = stapher.shifts_by_day(staphings)
		for i in range(0, len(shifts_by_day)):
			if shifts_by_day[i]:
				last_shift = shifts_by_day[i][len(shifts_by_day[i]) - 1]
				td = datetime.timedelta(hours = last_shift.end.hour, minutes = last_shift.end.minute)
			else:
				td = datetime.timedelta(hours = 6, minutes = 0)
			old_ending_shifts.append(td)
			if i != shift.day:
				new_ending_shifts.append(td)
			else:
				new_ending_shifts.append(datetime.timedelta(hours = shift.end.hour, minutes = shift.end.minute))
		old_avg = (sum(old_ending_shifts, datetime.timedelta()) / len(old_ending_shifts))
		new_avg = (sum(new_ending_shifts, datetime.timedelta()) / len(new_ending_shifts))
		change = new_avg - old_avg
	return change

def change_in_average_waketime(stapher, shift, staphings, all_shifts):
	change = datetime.timedelta(hours = 0, minutes = 0)
	previous_shift = stapher.get_previous_shift(shift, staphings)
	if not previous_shift:
		is_first_shift = True
	else:
		is_first_shift = shift.day != previous_shift.day
	if is_first_shift:
		old_starting_shifts = []
		new_starting_shifts = []
		shifts_by_day = stapher.shifts_by_day(staphings)
		for i in range(0, len(shifts_by_day)):
			if shifts_by_day[i]:
				first_shift = shifts_by_day[i][0]
				td = datetime.timedelta(hours = first_shift.start.hour, minutes = first_shift.start.minute)
			else:
				td = datetime.timedelta(hours = 23, minutes = 59)
			old_starting_shifts.append(td)
			if i != shift.day:
				new_starting_shifts.append(td)
			else:
				new_starting_shifts.append(datetime.timedelta(hours = shift.start.hour, minutes = shift.start.minute))
		old_avg = (sum(old_starting_shifts, datetime.timedelta()) / len(old_starting_shifts))
		new_avg = (sum(new_starting_shifts, datetime.timedelta()) / len(new_starting_shifts))
		change = old_avg - new_avg
	return change


def change_in_average_wake_and_bedtime(stapher, shift, staphings, all_shifts):
	wake_change = change_in_average_waketime(stapher, shift, staphings, all_shifts)
	bed_change = change_in_average_bedtime(stapher, shift, staphings, all_shifts)
	return wake_change + bed_change

def get_parameter_funtion(id):
	parameter_funtions = {
		1: get_scheduled_hours_in_shifts_day,
		2: get_total_scheduled_hours_in_schedule,
		3: get_number_of_shifts_with_any_matching_flags,
		4: get_number_of_shifts_with_all_matching_flags,
		5: get_time_between_last_and_next_shift,
		6: get_time_between_last_and_next_shift,
		7: hours_of_difficult_shifts_in_schedule,
		8: hours_of_difficult_shifts_in_day,
		9: hours_of_difficult_shifts_in_adjacent_days,
		10: change_in_sleep_window,
		11: number_of_other_shifts_stapher_could_cover,
		12: get_change_in_off_day_window,
		13: increase_in_people_worked_with,
		14: change_in_average_bedtime,
		15: change_in_average_waketime,
		16: change_in_average_wake_and_bedtime
	}
	return parameter_funtions[id]

def less_than(a, b):
	if a < b:
		return a
	else:
		return b

def greater_than(a, b):
	if a > b:
		return a
	else:
		return b

def get_cmp_funtion(p_id):
	cmp_funtions = {
		1: 	less_than,
		2: 	less_than,
		3: 	less_than,
		4: 	less_than,
		5: 	less_than,
		6: 	greater_than,
		7: 	less_than,
		8: 	less_than,
		9: 	less_than,
		10: less_than,
		11: less_than,
		12: less_than,
		13:	greater_than,
		14: greater_than,
		15: greater_than,
		16: greater_than
	}
	return cmp_funtions[p_id]

def get_parameter_scores(stapher, shift, staphings, parameters, all_shifts):
	scores = []
	for parameter in parameters:
		parameter_funtion = get_parameter_funtion(parameter.function_id)
		score = parameter_funtion(stapher, shift, staphings, all_shifts)
		scores.append(score)
	return scores

def get_best_scores(parameters, new_scores, best_scores):
	for parameter in parameters:
		cmp_funtion = get_cmp_funtion(parameter.function_id)
		print(f'****************************** Parameter = {parameter}, cmp_funtion = {cmp_funtion}')
		for i, score in enumerate(new_scores):
			best_scores[i] = cmp_funtion(score, best_scores[i])
	return best_scores
