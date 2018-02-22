
def get_scheduled_hours_in_shifts_day(stapher, shift, schedule):
	return stapher.hours_in_day(schedule, shift.day)

def get_total_scheduled_hours_in_schedule(stapher, shift, schedule):
	return stapher.total_hours(schedule)

def get_number_of_shifts_with_any_matching_flags(stapher, shift, schedule):
	return 0

def get_number_of_shifts_with_all_matching_flags(stapher, shift, schedule):
	return 0

def get_time_between_last_and_next_shift(stapher, shift, schedule):
	return 0


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


def get_parameter_scores(stapher, shift, schedule, parameters):
	scores = []
	for parameter in parameters:
		parameter_funtion = get_parameter_funtion(parameter.function_id)
		score = parameter_funtion(stapher, shift, schedule)
		scores.append(score)
	return scores

def get_best_scores(parameter_scores, reccomendation_info):
	return 2
