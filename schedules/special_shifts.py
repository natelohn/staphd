from operator import attrgetter

from .models import Schedule, Shift, Staphing, ShiftPreference


def swap(pref_a, pref_b):
	temp_ranking = -1
	saved_ranking = pref_a.ranking

	pref_a.ranking = temp_ranking
	pref_a.save() # Not the final ranking

	temp_ranking = pref_b.ranking
	pref_b.ranking = saved_ranking # pref_a's ranking
	pref_b.save()

	pref_a.ranking = temp_ranking # pref_b's ranking
	pref_a.save()


def swap_shift_preferences(to_swap, preferences, up):
	for i in range(1, len(preferences)):
		pref_a = preferences[i - 1]
		pref_b = preferences[i]
		if pref_a.ranking <= to_swap.ranking and to_swap.ranking <= pref_b.ranking:
			print(f'pref_a = {pref_a}')
			print(f'pref_b = {pref_b}')
			print(f'to_swap = {to_swap}')
			print(f'up = {up}')
			if up and pref_a != to_swap:
				print('up!')
				swap(pref_a, to_swap)
				break
			elif not up and pref_b != to_swap:
				print('down!')
				swap(to_swap, pref_b)
				break

def get_special_shift_flags():
	try:
		schedule = Schedule.objects.get(active = True)
		all_shifts = Shift.objects.filter(shift_set = schedule.shift_set)
		# Could just filter for shifts w/ the special shift flag to improve time.
	except:
		all_shifts = Shift.objects.all()
	all_special_flags = []
	for shift in all_shifts:
		if shift.is_special() and not shift.is_unpaid():
			new_flags = [flag for flag in shift.flags.all() if flag.title not in 'special' and flag not in all_special_flags]
			all_special_flags += new_flags
	return sorted(all_special_flags, key = attrgetter('title'))


def update_task_info(task, message, num, denom ):
	percent = int((num / denom) * 100)
	meta = {'message':message, 'process_percent':percent}
	task.update_state(meta = meta)

def get_suffix(rank):
	if rank == 1:
		return 'st'
	elif rank == 2:
		return 'nd'
	elif rank == 3:
		return 'rd'
	else:
		return 'th'


def place_special_shifts_by_rank(schedule, ordered_staphers, special_shifts, staphings, current_task):
	results = {}
	original_order = ordered_staphers[:]
	actions_taken = 0
	total_actions = len(ordered_staphers)
	update_task_info(current_task, 'Starting to Place Special Shifts', actions_taken,  total_actions)

	complete_staphers = []
	shifts_can_be_placed = True
	while shifts_can_be_placed:
		shifts_can_be_placed = False
		for stapher in ordered_staphers:
			update_message = f'Looking for a shift for {stapher}...'
			print(update_message)
			update_task_info(current_task, update_message, actions_taken, total_actions)
			shift_was_placed = False
			staphers_preferences = ShiftPreference.objects.filter(stapher = stapher).order_by('ranking')
			for rank, preference in enumerate(staphers_preferences):
				rank += 1
				if not shift_was_placed:
					for shift in special_shifts:
						if not shift_was_placed:
							can_take_shift = stapher.is_free(staphings, shift) and not shift.is_covered(staphings) 
							if can_take_shift and shift.has_flag(preference.flag):
								qual_str = ''
								for qual in shift.qualifications.all():
									if not qual in stapher.qualifications.all():
										stapher.qualifications.add(qual)
										qual_str += f'{qual}, '
										stapher.save()
								new_staphing = Staphing(schedule = schedule, stapher = stapher, shift = shift)
								suffix = get_suffix(rank)
								message = f'- Recieved their {rank}{suffix} choice \'{preference.flag}\' - {shift}. '
								if qual_str:
									message += f'(given the {qual_str[:-2]} qualifications for this shift)'
								new_staphing.save()
								staphings.append(new_staphing)
								shift_was_placed = True
			if shift_was_placed:
				shifts_can_be_placed = True
			else:
				message = f'{stapher} has no shifts availible given their preferences.'
				complete_staphers.append(stapher)
				actions_taken += 1


			if stapher.id in results:
				results[stapher.id].append(message)
			else:
				results[stapher.id] = [message]

		for stapher in complete_staphers:
			if stapher in ordered_staphers:
				ordered_staphers.remove(stapher)
	return [original_order, results]


		










