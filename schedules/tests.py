# import datetime

# from django.utils import timezone
from django.test import TestCase

from .models import Stapher, Shift


class StapherModelTests(TestCase):

    def test_test(self):
        """
        << ADD COMMENTS >>
        """
        self.assertIs(True, True)


class ShiftModelTests(TestCase):

    def test_end_time_is_before_start_time(self):
        """
        Test to make sure that Shifts can't have a start time after the end time.
        """
        s = Shift(start=1, end=0)
        s.save()
        qs = Shift.objects.all()
        self.assertQuerysetEqual(qs, [])

    def test_day_is_not_in_range(self):
        """
        Test to make sure that Shifts can't have a day that is not in the range of 0-6
        """
        s1 = Shift(day=7)
        s2 = Shift(day=-1)
        s1.save()
        s2.save()
        qs = Shift.objects.all()
        self.assertQuerysetEqual(qs, [])