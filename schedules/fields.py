from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import SmallIntegerField
from django.utils.translation import ugettext as _


DAY_OF_THE_WEEK = {
    0 : _(u'Sunday'),
    1 : _(u'Monday'),
    2 : _(u'Tuesday'),
    3 : _(u'Wednesday'),
    4 : _(u'Thursday'),
    5 : _(u'Friday'),
    6 : _(u'Saturday')
}

GENDER = {
    0 : 'Female',
    1 : 'Male',
    2 : 'Non-Binary',
    3 : 'Other'
}

TIE_OPTIONS = {
    0 : 'Automatically choose one of the people who tied at random.',
    1 : 'Automatically pick whoever won highest ranked parmeter.',
    2 : 'I want to choose whenever there is a tie.'
}

class DayOfTheWeekField(models.IntegerField):
    def __init__(self, *args, **kwargs):
        kwargs['choices'] = tuple(sorted(DAY_OF_THE_WEEK.items()))
        super(DayOfTheWeekField, self).__init__(*args, **kwargs)


class GenderField(models.IntegerField):
    def __init__(self, *args, **kwargs):
        kwargs['choices'] = tuple(sorted(GENDER.items()))
        super(GenderField, self).__init__(*args, **kwargs)


class TieBreakerField(models.IntegerField):
    def __init__(self, *args, **kwargs):
        kwargs['choices'] = tuple(sorted(TIE_OPTIONS.items()))
        super(TieBreakerField, self).__init__(*args, **kwargs)