from celery import current_task
from django.core.cache import cache
from operator import itemgetter
from random import random

from .excel import get_percent
from .models import Schedule, Staphing
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
def build_schedules(sorted_shifts, settings):
	print(f'			build_schedules executed')
	# Initialize the frontend information
	total_actions = cache.get('num_total_actions') or 1595 # TODO Remove Magic Number
	meta = {'message':'Starting to Build Schedules', 'process_percent':0}
	current_task.update_state(meta = meta)

	schedule = Schedule()
	schedule.save()
	staphings = []
	all_shifts = [shift[0] for shift in sorted_shifts]
	for shift, qualified_staphers in sorted_shifts:
		print(f'			placing shift: {shift}')
		if not shift.is_covered(staphings):
			free_and_qualified = get_free_staphers(qualified_staphers, shift, staphings)

			# Fail case, not enough qualified staphers to cover the shift
			if len(free_and_qualified) < shift.left_to_cover(staphings):
				for stapher in free_and_qualified:
					staphing = Staphing(stapher = stapher, shift = shift, schedule = schedule)
					staphings.append(staphing)

					# Update frontend information
					percent = get_percent(len(staphings), total_actions)
					meta = {'message':f'Auto scheduled {staphing}', 'process_percent':percent}
					current_task.update_state(meta = meta)
				left = shift.left_to_cover(staphings)
				meta = {'message':f'Could not schedule: {shift}. {left} more needed.', 'process_percent':percent}
				current_task.update_state(meta = meta)

			# In this system, all shifts that have no other options of people to cover them will be automatically scheduled.
			elif len(free_and_qualified) == shift.left_to_cover(staphings):
				for stapher in free_and_qualified:
					staphing = Staphing(stapher = stapher, shift = shift, schedule = schedule)
					staphings.append(staphing)

					# Update frontend information
					percent = get_percent(len(staphings), total_actions)
					meta = {'message':f'Auto scheduled {staphing}', 'process_percent':percent}
					current_task.update_state(meta = meta)

			# If the shift can be covered and there are more than just enough staphers to cover it, we make recommendations as to who should cover it
			# Depending on the settings, we either auto-schedule those recommendations or return them.
			else:
				recommendations = get_recommended_staphers(free_and_qualified, shift, staphings, settings, all_shifts)
				if not settings.auto_schedule:
					break
				else:
					ties_exist = do_ties_exist(recommendations, shift.left_to_cover(staphings))
					if ties_exist:
						if settings.user_breaks_ties():
							break
						else:
							recommendations = resolve_ties(settings, recommendations)
					recommendations_used = 0
					for stapher, scores, wins_losses in recommendations:
						wins = wins_losses.count(True)
						if wins >= settings.auto_threshold and not shift.is_covered(staphings):
							staphing = Staphing(stapher = stapher, shift = shift, schedule = schedule)
							staphings.append(staphing)
							recommendations_used += 1

							# Update frontend information
							percent = get_percent(len(staphings), total_actions)
							meta = {'message':f'Scheduled {staphing} on recommendation' , 'process_percent':percent}
							current_task.update_state(meta = meta)
							
					recommendations = recommendations[recommendations_used:]
	print(f'			** all shift looped **')
	# Update the frontend
	percent = get_percent(len(staphings), total_actions)
	meta = {'message':f'Saving Schedule', 'process_percent':percent}
	current_task.update_state(meta = meta)

	# Finally we save all the staphings that were made and return the Scheudle
	for staphing in staphings:
		staphing.save()
	return schedule
