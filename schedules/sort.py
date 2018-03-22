from operator import itemgetter
from random import shuffle

def get_qual_and_shifts_dicts(all_shifts):
	all_qualification_sets = set()
	set_id = 0
	qualification_set_qual_dict = {}
	qualification_set_shift_dict = {}
	for shift in all_shifts:
		qual_set = frozenset(shift.qualifications.all())

		# We have seen the set before
		if qual_set in all_qualification_sets:

			# Get the right Set ID
			for i in range(0,set_id):
				if qualification_set_qual_dict[i] == qual_set:
					break
			qualification_set_shift_dict[i].append(shift)

		# Our first time seeing the set
		else:
			qualification_set_qual_dict[set_id] = qual_set
			qualification_set_shift_dict[set_id] = [shift]
			all_qualification_sets.add(qual_set)
			set_id += 1
	return [qualification_set_qual_dict, qualification_set_shift_dict]

def get_stapher_dict(all_staphers, qual_dict):
	qualification_set_stapher_dict = {}
	for stapher in all_staphers:
		stapher_qualifications = frozenset(stapher.qualifications.all())
		for key in qual_dict:
			qual_set = qual_dict[key]
			# If the stapher is qualified...
			if qual_set.issubset(stapher_qualifications):
				# We have seen the set before
				if key in qualification_set_stapher_dict:
					qualification_set_stapher_dict[key].append(stapher)
				# Our first time seeing the set
				else:
					qualification_set_stapher_dict[key] = [stapher]
	return qualification_set_stapher_dict



def get_seconds_from_time(time):
	return (time.hour * 3600) + (time.minute * 60)

# This is a function designed to return all unique day + time pairs in order of earliest to latest.
# It is called in excel.py
def get_ordered_start_and_end_times_by_day(shifts):
	all_times_by_day = {}
	for shift in shifts:
		if shift.day in all_times_by_day:
			all_times_by_day[shift.day].add(shift.start)
			all_times_by_day[shift.day].add(shift.end)
		else:
			all_times_by_day[shift.day] = set([shift.start, shift.end])
	for day in all_times_by_day:
		sorted_list = list(all_times_by_day[day])
		sorted_list.sort(key = get_seconds_from_time)
		all_times_by_day[day] = sorted_list
	return all_times_by_day

# This is a funtion designed to return the seconds passed since sunday at midnight.
# Also called in excel.py
def get_seconds_from_day_and_time(day, time):
	day_seconds = int(day) * 24 * 60 * 60
	time_seconds = get_seconds_from_time(time)
	return day_seconds + time_seconds

# A function that returns the shifts in the order we would like to schedule them.
def get_sorted_shifts(staphers, shifts):
	print('Sorting Shifts in get_sorted_shifts...')
	sorted_shifts = []
	
	# First we get dictionaries mapping shifts with certain qualification sets to staphers who can cover those shifts.
	shift_and_qual_dicts = get_qual_and_shifts_dicts(shifts)
	qual_dict = shift_and_qual_dicts[0]
	shift_dict = shift_and_qual_dicts[1]
	stapher_dict = get_stapher_dict(staphers, qual_dict)

	# Used to optimize and reduce number of times needed to loop shifts
	ids_to_keys = {}
	total_needed_dict = {}

	# Used to check to track and compare a shift's ratio across different times.
	ids_to_ratio = {}

	# We loop all posible time windows given the shifts
	ordered_times_by_day = get_ordered_start_and_end_times_by_day(shifts)
	for day in ordered_times_by_day:
		times_for_day = ordered_times_by_day[day]
		for i in range(1, len(times_for_day)):
			start = times_for_day[i - 1]
			end = times_for_day[i]
			maxed_out_staphers = []
			maxed_out_shifts = []
			shifts_in_window = []
			time_key = get_seconds_from_day_and_time(day, start)

			# Get the sum of workers needed for all shifts with the same qualifications in the same time window
			for key in shift_dict:
				all_workers_needed = 0
				overlapping_shifts = []
				for shift in shift_dict[key]:
					if shift.is_in_window(day, start, end):
						ids_to_keys[shift.id] = key
						all_workers_needed += shift.workers_needed
						overlapping_shifts.append(shift)

				# Save the ammount of total workers needed for later
				if key in total_needed_dict:
					total_needed_dict[key][time_key] = all_workers_needed
				else:
					total_needed_dict[key] = {time_key: all_workers_needed}

				# Get the sum of staphers who can cover those shifts
				qualified_staphers = stapher_dict[key]

				# Check to see if the number is equal, if so, those staphers MUST cover those shifts to build a complete schedule.
				if all_workers_needed >= len(qualified_staphers):
					# Because of this, we don't want to schedule them for any other shifts in this time window so we will remove them 
					# 	from the availible staphers for other shifts.
					maxed_out_staphers.extend(qualified_staphers)
					maxed_out_shifts.extend(overlapping_shifts)
				shifts_in_window.extend(overlapping_shifts)

			# Find the best ratio for each shift in the window
			for shift in shifts_in_window:

				# First we get the total needed for shifts with the same qualifications in this window
				shift_key = ids_to_keys[shift.id]
				total_needed = total_needed_dict[shift_key][time_key]

				# If a shift has no qualifications, the ammount of workers needed is just the ammount the single shift requires.
				if not shift.qualifications.all():
					total_needed = shift.workers_needed

				# Next we get the total availible to cover this shift, accounting for maxed out staphers
				qualified_staphers = stapher_dict[shift_key]
				available_staphers = []
				if shift in maxed_out_shifts:
					available_staphers = qualified_staphers
				else:
					for stapher in qualified_staphers:
						if stapher not in maxed_out_staphers:
							available_staphers.append(stapher)

				# ** TEMP ** Used to improve schedules being front loaded.
				# TODO: Check to see why stapher order in the list matters when there are ties.
				shuffle(available_staphers)

				# We then use these ammounts to make a ratio used for sorting the shifts. The higher the ratio, the sooner it is scheduled.
				percent_of_staph_unavailable = 1 - (len(available_staphers) / staphers.count())
				ratio = (total_needed / len(available_staphers)) * percent_of_staph_unavailable

				# Now we will check to see if the ratio is higher than the last ratio.
				# If so, we will remove that shift from the array and replace it with the new ratio and save it for laster.
				# This keeps the shifts in the array unique and allows for the shift to get ratios from multiple time windows.
				if shift.id in ids_to_ratio:
					old_ratio = ids_to_ratio[shift.id][0]
					if ratio > old_ratio:
						ids_to_ratio[shift.id] = [ratio, shift.length(), shift, available_staphers]
				else:
					ids_to_ratio[shift.id] = [ratio, shift.length(), shift, available_staphers]

	# Now we add all the necessary information to the array.
	for key in ids_to_ratio:
		sorted_shifts.append(ids_to_ratio[key])

	# Finally, we return the shifts, sorted by ratio, then by length.
	return [[info[2], info[3]] for info in sorted(sorted_shifts, key = itemgetter(0,1), reverse = True)]


					





				





	








