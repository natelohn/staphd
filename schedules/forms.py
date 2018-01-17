from django import forms

from .models import Stapher, Shift


# def StapherCreateForm(forms.Form):
# 	first_name 		= forms.CharField()
# 	last_name 		= forms.CharField()
# 	title 			= forms.CharField()
# 	gender 			= forms.CharField()
# 	qualifications	= forms.TextField()
# 	age 			= forms.IntegerField()
# 	class_year 		= forms.IntegerField()
# 	summers_worked 	= forms.IntegerField()
# 	# Potentially Add Shifts Field


# 	# Need to implement for all above values^
# 	def clean_summers_worked(self):
# 		summers_worked = self.cleaned_data.get("summers_worked")
# 		if summers_worked < 0:
# 			raise forms.ValidationError("Must be a positive integer.")
# 		return summers_worked

class StapherCreateForm(forms.ModelForm):
	class Meta:
		model = Stapher
		fields = [
			'first_name',
			'last_name',
			'title',
			'gender',
			'qualifications',
			'age',
			'class_year',
			'summers_worked'
		]

	def clean_summers_worked(self):
		summers_worked = self.cleaned_data.get("summers_worked")
		if summers_worked < 0:
			raise forms.ValidationError("Must be a positive integer.")
		return summers_worked

class ShiftCreateForm(forms.ModelForm):
	class Meta:
		model = Shift
		fields = [
			'title',
			'flag',
			'start',
			'end',
			'qualifications',
			'workers_needed',
			'difficult',
			'on_sunday',
			'on_monday',
			'on_tuesday',
			'on_wednesday',
			'on_thursday',
			'on_friday',
			'on_saturday'
		]

