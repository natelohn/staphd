from .parameters import get_parameter_scores, get_best_scores

# Return the stapher that is reccomended based on the settings.
def get_recommended_stapher(staphers, shift, staphings, settings):
	parameters = settings.parameters.filter(use=True).order_by('rank')
	reccomendation_info = []
	for stapher in staphers:
		stapher_rec_info = [stapher]
		parameter_scores = get_parameter_scores(stapher, shift, staphings, parameters)
		stapher_rec_info.append(parameter_scores)
		reccomendation_info.append(stapher_rec_info)
	# for info in reccomendation_info:
	# 	print(info)
	# best_scores = get_best_scores(parameter_scores, reccomendation_info)
