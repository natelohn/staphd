import datetime

from itertools import combinations

from .sort import get_ordered_start_and_end_times_by_day, get_qual_and_shifts_dicts, get_stapher_dict



def clean_ratios(shifts, staphers, staphings):
	shift_and_qual_dicts = get_qual_and_shifts_dicts(shifts)
	shift_dict = shift_and_qual_dicts[1]
	stapher_dict = get_stapher_dict(staphers, shift_and_qual_dicts[0])
	all_q_sets = list(shift_dict.keys())
	print(all_q_sets)
	for i in range(1, len(all_q_sets)):
		print('A')
		for qs_set in list(combinations(all_q_sets, i)):
			print('B')
			sum_of_workers_needed = 0
			print('C')
			availible_workers = set()
			print('D')
			for qs in qs_set:
				print('E')
				sum_of_workers_needed += sum([s.workers_needed for s in shift_dict[q_set]])
				print('F')
				availible_workers = availible_workers | set([s.id for s in stapher_dict[q_set]])
				print('G')
				ratio = sum_of_workers_needed / availible_workers if availible_workers else sum_of_workers_needed + 1
				print('H')
				if ratio > 1:
					print('I')
					return False
	print('J')
	return True


def find_ratios(shifts, staphers, staphings):
	ordered_times_by_day = get_ordered_start_and_end_times_by_day(shifts)
	for day in ordered_times_by_day:
		for i in range(1, len(ordered_times_by_day[day])):
			start = ordered_times_by_day[day][i - 1]
			end = ordered_times_by_day[day][i]
			shifts_in_window = shifts.filter(day = day, start__lt = end, end__gt = start).order_by('workers_needed')
			clean = clean_ratios(shifts_in_window, staphers, staphings)
			if clean:
				print('clean')
			else:
				print('*************** UNCLEAN!! *****************')
