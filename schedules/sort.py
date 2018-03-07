from operator import itemgetter

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
def get_ordered_start_and_end_times_by_day(shifts):
	all_times_by_day = {}
	for shift in shifts:
		if shift.day in all_times_by_day:
			all_times_by_day[shift.day].add(shift.start)
			all_times_by_day[shift.day].add(shift.end)
		else:
			all_times_by_day[shift.day] = set()
	for day in all_times_by_day:
		sorted_list = list(all_times_by_day[day])
		sorted_list.sort(key = get_seconds_from_time)
		all_times_by_day[day] = sorted_list
	return all_times_by_day

# A function designed to return a list of the unique qualification sets, given a set of shifts
def get_qualification_sets(shifts):
	all_qualification_sets = set()
	for shift in shifts:
		qualification_set = frozenset(shift.qualifications.all())
		all_qualification_sets.add(qualification_set)
	return list(all_qualification_sets)


# Returns the list of staphers that could cover a shift with the same set of qualifications as those given
def get_qualified_staphers(staphers, qualifications):
	qualified_staphers = []
	for stapher in staphers:
		stapher_qs = frozenset(stapher.qualifications.all())
		if qualifications.issubset(stapher_qs):
			qualified_staphers.append(stapher)
	return qualified_staphers

# This is a funtion designed to return the seconds passed since sunday at midnight.
def get_seconds_from_day_and_time(day, time):
	day_seconds = int(day) * 24 * 60 * 60
	time_seconds = get_seconds_from_time(time)
	return day_seconds + time_seconds


# This is a function designed to take in a list of Shift and Stapher objects and return a dictionary
# 	with time windows as the key and an array of Shift/Staphers that must be covered/cover for that time.
def get_maxed_out_by_time(shifts, staphers):
	maxed_out_by_time = {}
	# First we loop all possible time windows given the shifts
	ordered_times_by_day = get_ordered_start_and_end_times_by_day(shifts)
	off_day_seen = False # Testing only 
	for day in ordered_times_by_day:
		times_for_day = ordered_times_by_day[day]
		for i in range(1, len(times_for_day)):
			start = times_for_day[i - 1]
			end = times_for_day[i]

			# Next we get all the shifts that are happening within that window.
			shifts_in_window = list(shifts.filter(day = str(day), start__lt = end, end__gt = start))

			# Then we get all the unique qualification sets for the shifts
			qualification_sets = get_qualification_sets(shifts_in_window)

			# Now we get the ammount of workers needed for each qualification set
			maxed_out_staphers = []
			maxed_out_shifts = []
			for q_set in qualification_sets:
				total_needed = 0
				shifts_in_set = []
				for shift in shifts_in_window:
					if q_set == frozenset(shift.qualifications.all()):
						total_needed += shift.workers_needed
						shifts_in_set.append(shift)
					if shift.id == 6706:
						off_day_seen = True
				
				# Finnaly, we see if the ammount of workers needed for a qualification set is greater than or equal to the ammount that are qualified
				staphers_qualified_for_set = get_qualified_staphers(staphers, q_set)
				if total_needed >= len(staphers_qualified_for_set):
					maxed_out_staphers.extend(staphers_qualified_for_set)
					maxed_out_shifts.extend(shifts_in_set)

			# Since we know each start and end pair is unique, we can use just the day and start as a key.
			key = get_seconds_from_day_and_time(day, start)
			maxed_out_by_time[key] = [maxed_out_shifts, maxed_out_staphers]
			if off_day_seen:
				print(f'{key} -> {maxed_out_shifts}\n{maxed_out_staphers}\n------------------------------------')
				off_day_seen = False

	return maxed_out_by_time


# This is a funtion designed to take in a shift, list of qualified staphers, and dictionary of staphers who have to take a shift at a given time.
# It returns the qualified staphers that DO NOT have to take any other shifts besides (perhaps) the one passed in.
def remove_unavailble_staphers(shift, qualified_staphers, maxed_out_by_time):
	# First we have to find all the shifts that are within a given time.
	start_key = get_seconds_from_day_and_time(shift.day, shift.start)
	end_key = get_seconds_from_day_and_time(shift.day, shift.end)
	unavailble_staphers = []
	for key in maxed_out_by_time:
		if start_key <= key and key < end_key:
			# print(f'{start_key} >= {key} < {end_key}')
			max_out_staphers = maxed_out_by_time[key][1]
			# if shift.id == 7197:
				# print(f'{max_out_staphers} ... are maxed out.\n----------------------------')
			# If the staphers that qualify for the given shift are a subset of maxed out then they must take the shift.
			if set(qualified_staphers).issubset(set(max_out_staphers)):
				# print(f'{shift} maxed out...')
				# if shift.id == 7197:
					# print(f'{qualified_staphers}\n <----- is a subset of --------> \n{max_out_staphers}...\n----------------------------')
				return qualified_staphers
			else:
				for stapher in max_out_staphers:
					if stapher not in unavailble_staphers:
						unavailble_staphers.append(stapher)
			# if shift.id == 7197:
				# print(f'{unavailble_staphers} ... are unavailble staphers. \n----------------------------')
	availble_staphers = []
	for stapher in qualified_staphers:
		if stapher not in unavailble_staphers and stapher not in availble_staphers:
			availble_staphers.append(stapher)
	if shift.id == 7028:
		print(f'{availble_staphers} ... are availble staphers.\n----------------------------')
	# print(f'{shift}\n{len(qualified_staphers)} -> {len(availble_staphers)} qualified.\n---------------------')
	
	return availble_staphers




def get_shift_info_array(shift_dict, stapher_dict, all_shifts, all_staphers):
	shifts_info = []
	count_of_staph = all_staphers.count()
	start = datetime.datetime.now()
	# maxed_out_by_time = get_maxed_out_by_time(all_shifts, all_staphers)
	# cache.set('maxed_out_by_time', maxed_out_by_time, None)
	maxed_out_by_time = cache.get('maxed_out_by_time')
	# print(f'Time to get maxed_out_by_time: {datetime.datetime.now() - start}')
	for key in shift_dict:
		qualified_staphers = stapher_dict[key]
		for shift in shift_dict[key]:
			qualified_free_staphers = remove_unavailble_staphers(shift, qualified_staphers, maxed_out_by_time)
			percent_of_staph_unqualified = (count_of_staph - len(qualified_free_staphers)) / count_of_staph
			ratio = (shift.workers_needed / len(qualified_free_staphers)) * percent_of_staph_unqualified
			shifts_info.append([ratio, shift, qualified_free_staphers])
	return shifts_info

def get_ratio(item):
	return item[0]


# # This function returns a list of shift sets sorted by the shift sets that require the most workers
# def sort_by_most_constrained_times(all_staphers, all_shifts):
# 	ordered_times_by_day = get_ordered_start_and_end_times_by_day(all_shifts)
# 	sorted_shifts = []
# 	count_of_staph = all_staphers.count()
# 	for day in ordered_times_by_day:
# 		times_for_day = ordered_times_by_day[day]
# 		for i in range(1, len(times_for_day)):
# 			start = times_for_day[i - 1]
# 			end = times_for_day[i]

# 			# get all overlapping shifts
# 			overlapping_shifts = list(all_shifts.filter(day = str(day), start__lt = end, end__gt = start))

# 			# find out how many workers are needed and how many qualify
# 			total_needed = 0
# 			all_qualifications = set()
# 			for shift in overlapping_shifts:
# 				if shift.qualifications.all():
# 					total_needed += shift.workers_needed 
# 			ratio = total_needed / count_of_staph
# 			sorted_overlap = sort_by_qualification(all_staphers, overlapping_shifts)
# 			sorted_shifts.append([ratio, sorted_overlap, day, start, end])

# 	# sort the array and return
# 	sorted_shifts.sort(reverse = True, key = get_ratio)
# 	# return [item[1] for item in sorted_shifts]
# 	return sorted_shifts


# A function that returns the shifts in the order we would like to schedule them.
# def get_sorted_shifts(staphers, shifts):
# 	print('Sorting Shifts in get_sorted_shifts...')
# 	# First we get all unique sets of qualifications
# 	# And we link them to the shifts that require them exactly
# 	shift_and_qual_dicts = get_qual_and_shifts_dicts(shifts)
# 	qual_dict = shift_and_qual_dicts[0]
# 	shift_dict = shift_and_qual_dicts[1]

# 	# Finally we link the unique sets of qualifications and link those to all the qualified staphers
# 	stapher_dict = get_stapher_dict(staphers, qual_dict)

# 	# Now we need to find how many staphers can work each shift
# 	sorted_shifts = get_shift_info_array(shift_dict, stapher_dict, shifts, staphers)
# 	sorted_shifts.sort(reverse = True, key = get_ratio)
# 	# return [[item[1], item[2]] for item in sorted_shifts]
# 	return sorted_shifts

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
					if int(day) == int(shift.day) and start < shift.end and end > shift.start:
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



				# We then use these ammounts to make a ratio used for sorting the shifts. The higher the ratio, the sooner it is scheduled.
				percent_of_staph_qualified = (staphers.count() - len(available_staphers)) / staphers.count()
				ratio = (total_needed / len(available_staphers)) * percent_of_staph_qualified

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
	return sorted(sorted_shifts, key = itemgetter(0,1), reverse = True)


					





				





	








