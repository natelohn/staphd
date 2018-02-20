from .models import Stapher, Shift

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


def get_shift_info_array(shift_dict, stapher_dict):
	shifts_info = []
	for key in shift_dict:
		qualified_staphers = stapher_dict[key]
		for shift in shift_dict[key]:
			ratio = shift.workers_needed / len(qualified_staphers)
			shifts_info.append([ratio, shift, qualified_staphers])
	return shifts_info

def getRatio(item):
	return item[0]

def get_sorted_shifts():
	# First we get all unique sets of qualifications
	# And we link them to the shifts that require them exactly
	all_shifts = Shift.objects.all()
	shift_and_qual_dicts = get_qual_and_shifts_dicts(all_shifts)
	qual_dict = shift_and_qual_dicts[0]
	shift_dict = shift_and_qual_dicts[1]
	# Finally we link the unique sets of qualifications and link those to all the qualified staphers
	all_staphers = Stapher.objects.all()
	stapher_dict = get_stapher_dict(all_staphers, qual_dict)
	# Now we need to find how many staphers can work each shift
	shift_info_array = get_shift_info_array(shift_dict, stapher_dict)
	shift_info_array.sort(reverse=True, key=getRatio)
	return shift_info_array

