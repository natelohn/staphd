from django.utils.translation import ugettext as _
from django.db import models
from django.db.models import SmallIntegerField

DAY_OF_THE_WEEK = {
    '0' : _(u'Sunday'),
    '1' : _(u'Monday'),
    '2' : _(u'Tuesday'),
    '3' : _(u'Wednesday'),
    '4' : _(u'Thursday'),
    '5' : _(u'Friday'),
    '6' : _(u'Saturday'), 
}

class DayOfTheWeekField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['choices']       = tuple(sorted(DAY_OF_THE_WEEK.items()))
        kwargs['max_length']    = 1 
        super(DayOfTheWeekField,self).__init__(*args, **kwargs)