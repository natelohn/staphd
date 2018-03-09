import datetime


def get_scheduled_hours_in_shifts_day(stapher, shift, staphings):
	return stapher.hours_in_day(staphings, shift.day)

def get_total_scheduled_hours_in_schedule(stapher, shift, staphings):
	return stapher.total_hours(staphings)

def get_number_of_shifts_with_any_matching_flags(stapher, shift, staphings):
	count_of_any_matching_flags = 0
	for staphing in staphings:
		if stapher == staphing.stapher and shift.has_matching_flags(staphing.shift):
			count_of_any_matching_flags += 1
	return count_of_any_matching_flags

def get_number_of_shifts_with_all_matching_flags(stapher, shift, staphings):
	count_of_all_matching_flags = 0
	for staphing in staphings:
		if stapher == staphing.stapher and shift.has_exact_flags(staphing.shift):
			count_of_all_matching_flags += 1
	return count_of_all_matching_flags

# Return the size of the length of time from the end of the shift before the given shift 
# 	and the start of the shift after the given shift.
def get_time_between_last_and_next_shift(stapher, shift, staphings):
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



def get_parameter_funtion(id):
	parameter_funtions = {
		1: get_scheduled_hours_in_shifts_day,
		2: get_total_scheduled_hours_in_schedule,
		3: get_number_of_shifts_with_any_matching_flags,
		4: get_number_of_shifts_with_all_matching_flags,
		5: get_time_between_last_and_next_shift,
		6: get_time_between_last_and_next_shift
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

def get_cmp_funtion(id):
	cmp_funtions = {
		1: less_than,
		2: less_than,
		3: less_than,
		4: less_than,
		5: less_than,
		6: greater_than
	}
	return cmp_funtions[id]



def get_parameter_scores(stapher, shift, staphings, parameters):
	scores = []
	for parameter in parameters:
		parameter_funtion = get_parameter_funtion(parameter.function_id)
		score = parameter_funtion(stapher, shift, staphings)
		scores.append(score)
	return scores

def get_best_scores(parameters, new_scores, best_scores):
	for parameter in parameters:
		cmp_funtion = get_cmp_funtion(parameter.function_id)
		for i, score in enumerate(new_scores):
			best_scores[i] = cmp_funtion(score, best_scores[i])
	return best_scores
