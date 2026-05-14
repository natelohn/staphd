from collections import defaultdict
from django.core.cache import cache
from operator import itemgetter
from random import random
from staphd.celery import app

from .excel import get_percent
from .models import Staphing
from .recommend import get_recommended_staphers


def recommendation_wins(rec):
	return rec[2].count(True)

def get_free_staphers(staphers, shift, staphings):
	free_staphers = []
	for stapher in staphers:
		if stapher.is_free(staphings, shift):
			free_staphers.append(stapher)
	return free_staphers

# This returns True if there are any recommended staphers in the array passed in that have the same ammount of wins
def do_ties_exist(recommendations, left_to_cover):
	for i in range(1, left_to_cover + 1):
		last_wins = recommendation_wins(recommendations[i - 1])
		next_wins = recommendation_wins(recommendations[i])
		if last_wins == next_wins:
			return True
	return False

# This returns the position of the highest ranked win
def highest_ranked_win(rec):
	if True in rec[2]:
		return rec[2].index(True)
	return len(rec[2])

# Returns the same list of staphers, but reordered based on the given settings to break ties.
def resolve_ties(settings, recommendations):
	for rec in recommendations:
		win_count = recommendation_wins(rec)
		if settings.break_ties_randomly():
			tie_breaker = random()
		elif settings.ranked_wins_break_ties():
			tie_breaker = highest_ranked_win(rec)
		else:
			tie_breaker = 0
		sorting_info = [(win_count * - 1), tie_breaker]
		rec.extend(sorting_info)
	recommendations = sorted(recommendations, key = itemgetter(3,4))
	return [[info[0], info[1], info[2]] for info in recommendations]

# Returns a schedule given the staphers, shifts and settings.
# Currently is not guarenteed to cover every shift.
# Covering 99% of shift w/ the 2017 shifts and staphers.
def build_schedules(sorted_shifts, settings, schedule, staphings, current_task):
	# Initialize the frontend information
	total_actions = cache.get('num_total_actions') or 1595 # TODO Remove Magic Number
	meta = {'message':'Starting to Build Schedules', 'process_percent':0}
	current_task.update_state(state='PROGRESS', meta=meta)

	# O(1) coverage and O(k) free-check structures — updated whenever a staphing is added.
	# Replaces O(n_staphings) scans on is_covered, left_to_cover, and is_free.
	coverage = defaultdict(int)
	stapher_intervals = defaultdict(list)
	for s in staphings:
		coverage[s.shift.id] += 1
		stapher_intervals[s.stapher.id].append((s.shift.day, s.shift.start, s.shift.end))

	def _is_covered(shift):
		return coverage[shift.id] >= shift.workers_needed

	def _workers_left(shift):
		return shift.workers_needed - coverage[shift.id]

	def _get_free_staphers(candidates, shift):
		free = []
		for stapher in candidates:
			intervals = stapher_intervals[stapher.id]
			if not any(d == shift.day and s < shift.end and e > shift.start for d, s, e in intervals):
				free.append(stapher)
		return free

	def _track(staphing):
		coverage[staphing.shift.id] += 1
		stapher_intervals[staphing.stapher.id].append(
			(staphing.shift.day, staphing.shift.start, staphing.shift.end)
		)

	parameters = list(settings.parameters.all().order_by('rank'))
	all_shifts = [shift[0] for shift in sorted_shifts]
	actions_taken = 0
	for shift, qualified_staphers in sorted_shifts:
		actions_taken += shift.workers_needed
		if not _is_covered(shift) and len(qualified_staphers) > 0:
			free_and_qualified = _get_free_staphers(qualified_staphers, shift)

			if len(free_and_qualified) > 0:
				# Fail case, not enough qualified staphers to cover the shift
				if len(free_and_qualified) < _workers_left(shift) and settings.auto_schedule:
					for stapher in free_and_qualified:
						staphing = Staphing(stapher = stapher, shift = shift, schedule = schedule)
						staphings.append(staphing)
						_track(staphing)

						# Update frontend information
						percent = get_percent(actions_taken, total_actions)
						meta = {'message':f'Auto scheduled {staphing}', 'process_percent':percent}
						current_task.update_state(state='PROGRESS', meta=meta)
					left = _workers_left(shift)
					percent = get_percent(actions_taken, total_actions)
					meta = {'message':f'Could not schedule: {shift}. {left} more needed.', 'process_percent':percent}
					current_task.update_state(state='PROGRESS', meta=meta)

				# In this system, all shifts that have no other options of people to cover them will be automatically scheduled when autoschedule is selected.
				elif len(free_and_qualified) == _workers_left(shift) and settings.auto_schedule:
					for stapher in free_and_qualified:
						staphing = Staphing(stapher = stapher, shift = shift, schedule = schedule)
						staphings.append(staphing)
						_track(staphing)

						# Update frontend information
						percent = get_percent(actions_taken, total_actions)
						meta = {'message':f'Auto scheduled {staphing}', 'process_percent':percent}
						current_task.update_state(state='PROGRESS', meta=meta)

				# If the shift can be covered and there are more than just enough staphers to cover it, we make recommendations as to who should cover it
				# Depending on the settings, we either auto-schedule those recommendations or return them.
				else:
					recommendations = get_recommended_staphers(free_and_qualified, shift, staphings, parameters, all_shifts)
					if not settings.auto_schedule:
						for staphing in staphings:
							staphing.save()
						return [shift, recommendations]
					else:
						ties_exist = do_ties_exist(recommendations, _workers_left(shift))
						if ties_exist:
							if settings.user_breaks_ties():
								for staphing in staphings:
									staphing.save()
								return [shift, recommendations]
							else:
								recommendations = resolve_ties(settings, recommendations)
						recommendations_used = 0
						for stapher, scores, wins_losses in recommendations:
							wins = wins_losses.count(True)
							if wins >= settings.auto_threshold and not _is_covered(shift):
								staphing = Staphing(stapher = stapher, shift = shift, schedule = schedule)
								staphings.append(staphing)
								_track(staphing)
								recommendations_used += 1

								# Update frontend information
								percent = get_percent(actions_taken, total_actions)
								meta = {'message':f'Scheduled {staphing} on recommendation' , 'process_percent':percent}
								current_task.update_state(state='PROGRESS', meta=meta)

						recommendations = recommendations[recommendations_used:]
						if not _is_covered(shift):
							for staphing in staphings:
								staphing.save()
							return [shift, recommendations]
	# Update the frontend
	percent = get_percent(actions_taken, total_actions)
	meta = {'message':f'Saving Schedule', 'process_percent':percent}
	current_task.update_state(state='PROGRESS', meta=meta)

	# Finally we save all the staphings that were made and return the Scheudle
	for staphing in staphings:
		staphing.save()
	return False
