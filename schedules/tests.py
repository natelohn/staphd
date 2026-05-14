import datetime
import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.conf import settings
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from .analytics import (
    get_hours_from_timedelta, get_td_from_time, get_hours_between_times,
    get_readable_time, get_str_from_td,
    get_average_window_between_shifts, get_people_not_worked_with,
)
from .build import get_free_staphers, do_ties_exist, highest_ranked_win
from .helpers import get_min, get_time_str, get_span_from_time, get_max_ratio
from .models import Stapher, Shift, Qualification, Schedule, ShiftSet, Staphing, Settings, Parameter
from .sort import (
    get_qual_and_shifts_dicts, get_stapher_dict, get_sorted_shifts,
    get_seconds_from_time, get_seconds_from_day_and_time, get_ordered_start_and_end_times_by_day,
)
from .recommend import get_recommended_staphers
from .tasks import RATIO_REDIRECT, RECOMMENDATION_REDIRECT, SPECIAL_SHIFT_REDIRECT

class StapherModelTests(TestCase):
    def setUp(self):
        ShiftSet.objects.create(pk=1, title='Default')

# ============================================================================
# -----------------------   STAPHER IS_QUALIFIED   --------------------------
# ============================================================================
    def test_is_qualified_stapher_has_same_qualifications_for_shift(self):
        # Make sure is_qualified is working when the shift and stapher have the same qualifications
        stapher = Stapher(gender=0)
        stapher.save()
        shift = Shift()
        shift.save()
        q1 = Qualification(title = 'one')
        q1.save()
        q2 = Qualification(title = 'two')
        q2.save()
        shift.qualifications.add(q1)
        shift.qualifications.add(q2)
        stapher.qualifications.add(q1)
        stapher.qualifications.add(q2)
        self.assertTrue(stapher.is_qualified(shift))


    def test_is_qualified_stapher_has_more_qualifications_than_shift(self):
        # Make sure is_qualified is working when the shift and stapher have the same qualifications
        stapher = Stapher(gender=0)
        stapher.save()
        shift = Shift()
        shift.save()
        q1 = Qualification(title = 'one')
        q1.save()
        q2 = Qualification(title = 'two')
        q2.save()
        shift.qualifications.add(q1)
        stapher.qualifications.add(q1)
        stapher.qualifications.add(q2)
        self.assertTrue(stapher.is_qualified(shift))


    def test_is_qualified_stapher_has_less_qualifications_than_shift(self):
        # Make sure is_qualified is working when the shift and stapher have the same qualifications
        stapher = Stapher(gender=0)
        stapher.save()
        shift = Shift()
        shift.save()
        q1 = Qualification(title = 'one')
        q1.save()
        q2 = Qualification(title = 'two')
        q2.save()
        shift.qualifications.add(q1)
        shift.qualifications.add(q2)
        stapher.qualifications.add(q1)
        self.assertFalse(stapher.is_qualified(shift))

    def test_is_qualified_stapher_has_no_qualifications(self):
        # Make sure is_qualified is working when the shift and stapher have the same qualifications
        stapher = Stapher(gender=0)
        stapher.save()
        shift = Shift()
        shift.save()
        q1 = Qualification(title = 'one')
        q1.save()
        shift.qualifications.add(q1)
        self.assertFalse(stapher.is_qualified(shift))

    def test_is_qualified_shift_has_no_qualifications(self):
        # Make sure is_qualified is working when the shift and stapher have the same qualifications
        stapher = Stapher(gender=0)
        stapher.save()
        shift = Shift()
        shift.save()
        q1 = Qualification(title = 'one')
        q1.save()
        stapher.qualifications.add(q1)
        self.assertTrue(stapher.is_qualified(shift))

# ============================================================================
# --------------------------   STAPHER IS_FREE  ------------------------------
# ============================================================================
    def test_is_free_stapher_not_free(self):
        # Make sure is_free is working when the stapher has a shift at the same time
        stapher = Stapher(gender=0)
        stapher.save()
        shift1 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 10))
        shift1.save()
        shift2 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 10))
        shift2.save()
        schedule = Schedule()
        schedule.save()
        staphing = Staphing(stapher = stapher, shift = shift1, schedule = schedule)
        self.assertFalse(stapher.is_free([staphing], shift2))


    def test_is_free_stapher_not_free_same_shift(self):
        # Make sure is_free is working when the stapher has the same shift scheduled
        stapher = Stapher(gender=0)
        stapher.save()
        shift1 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 10))
        shift1.save()
        schedule = Schedule()
        schedule.save()
        staphing = Staphing(stapher = stapher, shift = shift1, schedule = schedule)
        self.assertFalse(stapher.is_free([staphing], shift1))


    def test_is_free_stapher_has_no_shifts(self):
        # Make sure is_free is working when the stapher has no shifts
        stapher = Stapher(gender=0)
        shift1 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 10))
        self.assertTrue(stapher.is_free([], shift1))

    def test_is_free_stapher_is_free(self):
        # Make sure is_free is working when the stapher has a shift that doesn't overlap scheduled
        stapher = Stapher(gender=0)
        stapher.save()
        shift1 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 10))
        shift1.save()
        shift2 = Shift(start = datetime.time(hour = 10), end = datetime.time(hour = 11))
        shift2.save()
        schedule = Schedule()
        schedule.save()
        staphing = Staphing(stapher = stapher, shift = shift1, schedule = schedule)
        self.assertTrue(stapher.is_free([staphing], shift2))
    
    def test_is_free_stapher_has_two_overlaping_shifts(self):
        # Make sure is_free is working when the stapher has two shifts that overlap
        stapher = Stapher(gender=0)
        stapher.save()
        shift1 = Shift(start = datetime.time(hour = 8), end = datetime.time(hour = 10))
        shift1.save()
        shift2 = Shift(start = datetime.time(hour = 11), end = datetime.time(hour = 14))
        shift2.save()
        shift3 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 12))
        shift3.save()
        schedule = Schedule()
        schedule.save()
        staphing1 = Staphing(stapher = stapher, shift = shift1, schedule = schedule)
        staphing2 = Staphing(stapher = stapher, shift = shift2, schedule = schedule)
        self.assertFalse(stapher.is_free([staphing1, staphing2], shift3))

    def test_is_free_stapher_has_overlaping_shift_on_different_day(self):
        # Make sure is_free is working when the stapher has a shift at the same time on a different day
        stapher = Stapher(gender=0)
        stapher.save()
        shift1 = Shift(day = 0, start = datetime.time(hour = 8), end = datetime.time(hour = 10))
        shift1.save()
        shift2 = Shift(day = 1, start = datetime.time(hour = 8), end = datetime.time(hour = 10))
        shift2.save()
        schedule = Schedule()
        schedule.save()
        staphing = Staphing(stapher = stapher, shift = shift1, schedule = schedule)
        self.assertTrue(stapher.is_free([staphing], shift2))

# ============================================================================
# ------------------------   STAPHER HOURS_IN_DAY  ---------------------------
# ============================================================================
    def test_hours_in_day_no_shifts(self):
        stapher = Stapher(gender=0)
        self.assertEquals(stapher.hours_in_day([], 0).seconds, 0)

    def test_hours_in_day_one_hour_shifts(self):
        stapher = Stapher(gender=0)
        shift = Shift()
        schedule = Schedule()
        staphing = Staphing(stapher = stapher, shift = shift, schedule = schedule)
        seconds_in_hour = 60 * 60
        self.assertEquals(stapher.hours_in_day([staphing], 0).seconds, seconds_in_hour)

    def test_hours_in_day_two_one_hour_shifts(self):
        stapher = Stapher(gender=0)
        shift1 = Shift()
        shift2 = Shift()
        schedule = Schedule()
        staphing1 = Staphing(stapher = stapher, shift = shift1, schedule = schedule)
        staphing2 = Staphing(stapher = stapher, shift = shift2, schedule = schedule)
        seconds_in_hour = 60 * 60
        self.assertEquals(stapher.hours_in_day([staphing1, staphing2], 0).seconds, seconds_in_hour * 2)

    def test_hours_in_day_two_one_hour_shifts_different_days(self):
        stapher = Stapher(gender=0)
        shift1 = Shift()
        shift2 = Shift(day=1)
        schedule = Schedule()
        staphing1 = Staphing(stapher = stapher, shift = shift1, schedule = schedule)
        staphing2 = Staphing(stapher = stapher, shift = shift2, schedule = schedule)
        seconds_in_hour = 60 * 60
        self.assertEquals(stapher.hours_in_day([staphing1, staphing2], 0).seconds, seconds_in_hour)

# ============================================================================
# -------------------------   STAPHER TOTAL_HOURS  ---------------------------
# ============================================================================
    def test_total_hours_no_shifts(self):
        stapher = Stapher(gender=0)
        self.assertEquals(stapher.total_hours([]).seconds, 0)

    def test_total_hours_one_hour_shifts(self):
        stapher = Stapher(gender=0)
        shift = Shift()
        schedule = Schedule()
        staphing = Staphing(stapher = stapher, shift = shift, schedule = schedule)
        seconds_in_hour = 60 * 60
        self.assertEquals(stapher.total_hours([staphing]).seconds, seconds_in_hour)

    def test_total_hours_two_one_hour_shifts(self):
        stapher = Stapher(gender=0)
        shift1 = Shift()
        shift2 = Shift()
        schedule = Schedule()
        staphing1 = Staphing(stapher = stapher, shift = shift1, schedule = schedule)
        staphing2 = Staphing(stapher = stapher, shift = shift2, schedule = schedule)
        seconds_in_hour = 60 * 60
        self.assertEquals(stapher.total_hours([staphing1, staphing2]).seconds, seconds_in_hour * 2)

    def test_total_hours_two_one_hour_shifts_different_days(self):
        stapher = Stapher(gender=0)
        shift1 = Shift()
        shift2 = Shift(day=1)
        schedule = Schedule()
        staphing1 = Staphing(stapher = stapher, shift = shift1, schedule = schedule)
        staphing2 = Staphing(stapher = stapher, shift = shift2, schedule = schedule)
        seconds_in_hour = 60 * 60
        self.assertEquals(stapher.total_hours([staphing1, staphing2]).seconds, seconds_in_hour * 2)

    def test_total_hours_three_one_hour_shifts_different_days(self):
        stapher = Stapher(gender=0)
        shift1 = Shift()
        shift2 = Shift(day=1)
        shift3 = Shift(day=2)
        schedule = Schedule()
        staphing1 = Staphing(stapher = stapher, shift = shift1, schedule = schedule)
        staphing2 = Staphing(stapher = stapher, shift = shift2, schedule = schedule)
        staphing3 = Staphing(stapher = stapher, shift = shift3, schedule = schedule)
        seconds_in_hour = 60 * 60
        self.assertEquals(stapher.total_hours([staphing1, staphing2, staphing3]).seconds, seconds_in_hour * 3)

class ShiftModelTests(TestCase):
    def setUp(self):
        ShiftSet.objects.create(pk=1, title='Default')

# ============================================================================
# -----------------------------   SHIFT SAVE  --------------------------------
# ============================================================================
    def test_end_time_is_start_time(self):
        # Test to make sure that Shifts can't have the same start time and end time.
        s = Shift(start = datetime.time(hour = 11), end = datetime.time(hour = 11))
        s.save()
        qs = Shift.objects.all()
        self.assertQuerysetEqual(qs, [])


    def test_end_time_is_before_start_time(self):
        # Test to make sure that Shifts can't have a start time after the end time.
        s = Shift(start = datetime.time(hour = 11), end = datetime.time(hour = 10))
        s.save()
        qs = Shift.objects.all()
        self.assertQuerysetEqual(qs, [])

    def test_day_is_not_in_range(self):
        # Test to make sure that Shifts can't have a day that is not in the range of 0-6
        s1 = Shift(day = 7)
        s2 = Shift(day = -1)
        s1.save()
        s2.save()
        qs = Shift.objects.all()
        self.assertQuerysetEqual(qs, [])

    def test_valid_save(self):
        # Test to make sure that Shifts can't have a start time after the end time.
        s = Shift(start = datetime.time(hour = 11), end = datetime.time(hour = 12))
        s.save()
        qs = Shift.objects.all()
        self.assertNotEqual(qs, [])

# ============================================================================
# ---------------------------   SHIFT OVERLAPS  ------------------------------
# ============================================================================

    # Case 1: Start 1 < Start 2, End 1 < Start 2, Start 1 < End 2, End 1 < End 2 -> False
    # Case 2: Start 1 < Start 2, End 1 = Start 2, Start 1 < End 2, End 1 < End 2 -> False
    # Case 3: Start 1 < Start 2, End 1 > Start 2, Start 1 < End 2, End 1 < End 2 -> True
    # Case 4: Start 1 = Start 2, End 1 > Start 2, Start 1 < End 2, End 1 < End 2 -> True
    # Case 5: Start 1 = Start 2, End 1 > Start 2, Start 1 < End 2, End 1 = End 2 -> True
    # Case 6: Start 1 > Start 2, End 1 > Start 2, Start 1 < End 2, End 1 = End 2 -> True
    # Case 7: Start 1 > Start 2, End 1 > Start 2, Start 1 < End 2, End 1 > End 2 -> True
    # Case 8: Start 1 > Start 2, End 1 > Start 2, Start 1 = End 2, End 1 > End 2 -> False
    # Case 9: Start 1 > Start 2, End 1 > Start 2, Start 1 > End 2, End 1 > End 2 -> False
    # Case 10: Start 1 < Start 2, End 1 > Start 2, Start 1 < End 2, End 1 > End 2 -> True
    # Case 11: Start 1 > Start 2, End 1 > Start 2, Start 1 < End 2, End 1 < End 2 -> True
    # Case 12: overlaps, but on different days

    def test_overlaps_case_1(self):
        s1 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 10))
        s1.save()
        s2 = Shift(start = datetime.time(hour = 11), end = datetime.time(hour = 12))
        s2.save()
        self.assertFalse(s1.overlaps(s2))

    def test_overlaps_case_2(self):
        s1 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 10))
        s1.save()
        s2 = Shift(start = datetime.time(hour = 10), end = datetime.time(hour = 11))
        s2.save()
        self.assertFalse(s1.overlaps(s2))

    def test_overlaps_case_3(self):
        s1 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 11))
        s1.save()
        s2 = Shift(start = datetime.time(hour = 10), end = datetime.time(hour = 12))
        s2.save()
        self.assertTrue(s1.overlaps(s2))

    def test_overlaps_case_4(self):
        s1 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 11))
        s1.save()
        s2 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 12))
        s2.save()
        self.assertTrue(s1.overlaps(s2))

    def test_overlaps_case_5(self):
        s1 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 11))
        s1.save()
        s2 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 11))
        s2.save()
        self.assertTrue(s1.overlaps(s2))


    def test_overlaps_case_6(self):
        s1 = Shift(start = datetime.time(hour = 10), end = datetime.time(hour = 11))
        s1.save()
        s2 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 11))
        s2.save()
        self.assertTrue(s1.overlaps(s2))

    def test_overlaps_case_7(self):
        s1 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 11))
        s1.save()
        s2 = Shift(start = datetime.time(hour = 8), end = datetime.time(hour = 10))
        s2.save()
        self.assertTrue(s1.overlaps(s2))

    def test_overlaps_case_8(self):
        s1 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 11))
        s1.save()
        s2 = Shift(start = datetime.time(hour = 8), end = datetime.time(hour = 9))
        s2.save()
        self.assertFalse(s1.overlaps(s2))

    def test_overlaps_case_9(self):
        s1 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 11))
        s1.save()
        s2 = Shift(start = datetime.time(hour = 7), end = datetime.time(hour = 8))
        s2.save()
        self.assertFalse(s1.overlaps(s2))

    def test_overlaps_case_10(self):
        s1 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 13))
        s1.save()
        s2 = Shift(start = datetime.time(hour = 10), end = datetime.time(hour = 12))
        s2.save()
        self.assertTrue(s1.overlaps(s2))

    def test_overlaps_case_11(self):
        s1 = Shift(start = datetime.time(hour = 10), end = datetime.time(hour = 11))
        s1.save()
        s2 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 12))
        s2.save()
        self.assertTrue(s1.overlaps(s2))

    def test_overlaps_case_12(self):
        s1 = Shift(day = 0, start = datetime.time(hour = 9), end = datetime.time(hour = 11))
        s1.save()
        s2 = Shift(day = 1, start = datetime.time(hour = 9), end = datetime.time(hour = 11))
        s2.save()
        self.assertFalse(s1.overlaps(s2))

# ============================================================================
# --------------------------   SHIFT IS_COVERED  -----------------------------
# ============================================================================
    def test_is_covered_shift_is_covered(self):
        # Test to make sure is_covered is working when shift that needs 1 worker has 1 worker
        shift = Shift(workers_needed = 1)
        shift.save()
        stapher = Stapher(gender=0)
        stapher.save()
        schedule = Schedule()
        schedule.save()
        staphing = Staphing(shift = shift, stapher = stapher, schedule = schedule)
        self.assertTrue(shift.is_covered([staphing]))

    def test_is_covered_shift_that_needs_three_is_covered(self):
        # Test to make sure is_covered is working when shift that needs 3 workers has 3 workers
        shift = Shift(workers_needed = 3)
        shift.save()
        stapher1 = Stapher(gender=0)
        stapher1.save()
        stapher2 = Stapher(gender=0)
        stapher2.save()
        stapher3 = Stapher(gender=0)
        stapher3.save()
        schedule = Schedule()
        schedule.save()
        staphing1 = Staphing(shift = shift, stapher = stapher1, schedule = schedule)
        staphing2 = Staphing(shift = shift, stapher = stapher2, schedule = schedule)
        staphing3 = Staphing(shift = shift, stapher = stapher3, schedule = schedule)
        self.assertTrue(shift.is_covered([staphing1, staphing2, staphing3]))

    def test_is_covered_shift_is_not_covered(self):
        # Test to make sure is_covered is working when shift that needs 1 worker has 0 workers
        shift = Shift(workers_needed = 1)
        shift.save()
        self.assertFalse(shift.is_covered([]))

    def test_is_covered_shift_that_needs_three_is_not_covered(self):
        # Test to make sure is_covered is working when shift that needs 3 workers has 2 workers
        shift = Shift(workers_needed = 3)
        shift.save()
        stapher1 = Stapher(gender=0)
        stapher1.save()
        stapher2 = Stapher(gender=0)
        stapher2.save()
        schedule = Schedule()
        schedule.save()
        staphing1 = Staphing(shift = shift, stapher = stapher1, schedule = schedule)
        staphing2 = Staphing(shift = shift, stapher = stapher2, schedule = schedule)
        self.assertFalse(shift.is_covered([staphing1, staphing2]))

# ============================================================================
# ----------------------------   SHIFT LENGTH  -------------------------------
# ============================================================================
    def test_length_as_default(self):
        shift = Shift()
        seconds_in_hour = 60 * 60
        self.assertEquals(shift.length().seconds , seconds_in_hour)

    def test_length_day_is_zero(self):
        shift = Shift(day = 4)
        self.assertEquals(shift.length().days, 0)

    def test_length_day_is_zero_as_default(self):
        shift = Shift()
        self.assertEquals(shift.length().days, 0)

    def test_length_long_shift(self):
        shift = Shift(start = datetime.time(1, 0, 0, 0), end = datetime.time(21, 0, 0, 0))
        seconds_in_hour = 60 * 60
        self.assertEquals(shift.length().seconds, seconds_in_hour * 20)

    def test_length_15_minutes(self):
        shift = Shift(start = datetime.time(1, 0, 0, 0), end = datetime.time(1, 15, 0, 0))
        seconds_in_hour = 60 * 60 
        self.assertEquals(shift.length().seconds, seconds_in_hour * 0.25)

    def test_length_20_minutes(self):
        shift = Shift(start = datetime.time(1, 0, 0, 0), end = datetime.time(1, 20, 0, 0))
        seconds_in_hour = 60 * 60 
        self.assertEquals(shift.length().seconds, seconds_in_hour * (1/3))

    def test_length_30_minutes(self):
        shift = Shift(start = datetime.time(1, 0, 0, 0), end = datetime.time(1, 30, 0, 0))
        seconds_in_hour = 60 * 60 
        self.assertEquals(shift.length().seconds, seconds_in_hour * 0.5)

    def test_length_40_minutes(self):
        shift = Shift(start = datetime.time(1, 0, 0, 0), end = datetime.time(1, 40, 0, 0))
        seconds_in_hour = 60 * 60 
        self.assertEquals(shift.length().seconds, seconds_in_hour * (2/3))

    def test_length_45_minutes(self):
        shift = Shift(start = datetime.time(1, 0, 0, 0), end = datetime.time(1, 45, 0, 0))
        seconds_in_hour = 60 * 60 
        self.assertEquals(shift.length().seconds, seconds_in_hour * 0.75)

    def test_length_start_end_at_half_hour(self):
        shift = Shift(start = datetime.time(1, 30, 0, 0), end = datetime.time(2, 30, 0, 0))
        seconds_in_hour = 60 * 60 
        self.assertEquals(shift.length().seconds, seconds_in_hour)

    def test_length_start_min_more_than_end_min(self):
        shift = Shift(start = datetime.time(1, 45, 0, 0), end = datetime.time(2, 15, 0, 0))
        seconds_in_hour = 60 * 60 
        self.assertEquals(shift.length().seconds, seconds_in_hour * (1/2))

    def test_length_comparing(self):
        shift1 = Shift(start = datetime.time(1, 0, 0, 0), end = datetime.time(2, 0, 0, 0))
        shift2 = Shift(start = datetime.time(1, 0, 0, 0), end = datetime.time(3, 0, 0, 0))
        shift3 = Shift(start = datetime.time(2, 0, 0, 0), end = datetime.time(3, 0, 0, 0))
        self.assertTrue(shift1.length() < shift2.length())
        self.assertFalse(shift1.length() > shift2.length())
        self.assertTrue(shift1.length() == shift3.length())

# ============================================================================
# ------------------------   SHIFT LEFT_TO_COVER  ----------------------------
# ============================================================================

    def test_left_to_cover_non_covered(self):
        shift = Shift()
        self.assertEquals(shift.workers_needed, shift.left_to_cover([]))

    def test_left_to_cover_is_covered(self):
        shift = Shift(workers_needed = 1)
        stapher = Stapher(gender=0)
        schedule = Schedule()
        shift.save()
        stapher.save()
        schedule.save()
        staphing = Staphing(stapher = stapher, shift = shift, schedule = schedule)
        self.assertTrue(shift.left_to_cover([staphing]) == 0)

    def test_left_to_cover_partially_covered(self):
        shift = Shift(workers_needed = 2)
        stapher = Stapher(gender=0)
        schedule = Schedule()
        shift.save()
        stapher.save()
        schedule.save()
        staphing = Staphing(stapher = stapher, shift = shift, schedule = schedule)
        self.assertTrue(shift.left_to_cover([staphing]) == 1) 

class SettingsModelTests(TestCase):
# ============================================================================
# --------------------   SETTINGS BREAK_TIES_RANDOMLY  -----------------------
# ============================================================================
    def test_break_ties_randomly_true_as_default(self):
        settings = Settings()
        self.assertTrue(settings.break_ties_randomly())

    def test_break_ties_randomly_false(self):
        settings = Settings(tie_breaker = 1)
        self.assertFalse(settings.break_ties_randomly())

    def test_break_ties_randomly_true(self):
        settings = Settings(tie_breaker = 0)
        self.assertTrue(settings.break_ties_randomly())

# ============================================================================
# -------------------   SETTINGS RANKED_WINS_BREAK_TIES  ---------------------
# ============================================================================
    def test_ranked_wins_break_ties_false_as_default(self):
        settings = Settings()
        self.assertFalse(settings.ranked_wins_break_ties())

    def test_ranked_wins_break_ties_false(self):
        settings = Settings(tie_breaker = 0)
        self.assertFalse(settings.ranked_wins_break_ties())

    def test_ranked_wins_break_ties_true(self):
        settings = Settings(tie_breaker = 1)
        self.assertTrue(settings.ranked_wins_break_ties())

# ============================================================================
# ----------------------   SETTINGS USER_BREAK_TIES  -------------------------
# ============================================================================
    def test_user_breaks_ties_false_as_default(self):
        settings = Settings()
        self.assertFalse(settings.user_breaks_ties())

    def test_user_breaks_ties_false(self):
        settings = Settings(tie_breaker = 0)
        self.assertFalse(settings.user_breaks_ties())

    def test_user_breaks_ties_true(self):
        settings = Settings(tie_breaker = 2)
        self.assertTrue(settings.user_breaks_ties())

class SortTests(TestCase):
    fixtures = [
        'shiftset.json',
        'flags.json',
        'qualifications.json',
        'staphers.json',
        'shifts.json',
    ]
# ============================================================================
# ---------------------   get_qual_and_shifts_dicts  -------------------------
# ============================================================================
    def test_get_qual_and_shifts_dicts_keys_match(self):
        all_keys_match = True
        all_shifts = Shift.objects.all()
        arrays = get_qual_and_shifts_dicts(all_shifts)
        qual_dict = arrays[0]
        shift_dict = arrays[1]
        for key in qual_dict:
            if key not in shift_dict:
                all_keys_match = False
        for key in shift_dict:
            if key not in qual_dict:
                all_keys_match = False
        self.assertTrue(all_keys_match)

    def test_get_qual_and_shifts_dicts_all_shifts_found(self):
        all_shifts_found = True
        all_shifts = Shift.objects.all()
        arrays = get_qual_and_shifts_dicts(all_shifts)
        shift_dict = arrays[1]
        found_shifts = []
        for key in shift_dict:
            found_shifts.extend(shift_dict[key])
        for shift in all_shifts:
            if shift not in found_shifts:
                all_shifts_found = False
                break
        self.assertTrue(all_shifts_found)

    def test_get_qual_and_shifts_dicts_all_quals_found(self):
        all_quals_found = True
        all_shifts = Shift.objects.all()
        arrays = get_qual_and_shifts_dicts(all_shifts)
        qual_dict = arrays[0]
        found_quals = []
        for key in qual_dict:
            found_quals.append(qual_dict[key])
        for shift in all_shifts:
            if frozenset(shift.qualifications.all()) not in found_quals:
                all_quals_found = False
                break
        self.assertTrue(all_quals_found)

# ============================================================================
# -------------------------   get_stapher_dict  ------------------------------
# ============================================================================
    def test_get_stapher_dict_keys_match(self):
        all_keys_match = True
        all_shifts = Shift.objects.all()
        arrays = get_qual_and_shifts_dicts(all_shifts)
        qual_dict = arrays[0]
        all_staphers = Stapher.objects.all()
        stapher_dict = get_stapher_dict(all_staphers, qual_dict)
        for key in qual_dict:
            if key not in stapher_dict:
                all_keys_match = False
        for key in stapher_dict:
            if key not in qual_dict:
                all_keys_match = False
        self.assertTrue(all_keys_match)

    def test_get_stapher_dict_keys_match(self):
        all_staphers_found = True
        all_shifts = Shift.objects.all()
        arrays = get_qual_and_shifts_dicts(all_shifts)
        qual_dict = arrays[0]
        all_staphers = Stapher.objects.all()
        stapher_dict = get_stapher_dict(all_staphers, qual_dict)
        found_staphers = []
        for key in stapher_dict:
            found_staphers.extend(stapher_dict[key])
        for stapher in all_staphers:
            if stapher not in found_staphers:
                all_staphers_found = False
                break
        self.assertTrue(all_staphers_found)

    def test_get_stapher_dict_keys_match(self):
        all_staphers_qualify = True
        all_shifts = Shift.objects.all()
        arrays = get_qual_and_shifts_dicts(all_shifts)
        qual_dict = arrays[0]
        shifts_dict = arrays[1]
        all_staphers = Stapher.objects.all()
        stapher_dict = get_stapher_dict(all_staphers, qual_dict)
        for key in qual_dict:
            shifts = shifts_dict[key]
            staphers = stapher_dict[key]
            for stapher in staphers:
                for shift in shifts:
                    if not stapher.is_qualified(shift):
                        all_staphers_qualify = False
        self.assertTrue(all_staphers_qualify)

# ============================================================================
# ------------------------   get_sorted_shifts  ------------------------------
# ============================================================================

    def test_get_sorted_shifts_returns_shift_stapher_pairs(self):
        sorted_shifts = get_sorted_shifts(Stapher.objects.all(), Shift.objects.all())
        self.assertIsInstance(sorted_shifts, list)
        for item in sorted_shifts:
            self.assertEqual(len(item), 2)
            self.assertIsInstance(item[0], Shift)
            self.assertIsInstance(item[1], list)

class BuildTests(TestCase):
# ============================================================================
# ------------------------   get_free_staphers  ------------------------------
# ============================================================================
    
    def test_get_free_staphers_one_stapher_free(self):
        stapher1 = Stapher(gender=0)
        stapher1.save()
        stapher2 = Stapher(gender=0)
        stapher2.save()
        busy_shift = Shift(start=datetime.time(hour=9), end=datetime.time(hour=10))
        target_shift = Shift(start=datetime.time(hour=9), end=datetime.time(hour=10))
        schedule = Schedule()
        staphing = Staphing(stapher=stapher1, shift=busy_shift, schedule=schedule)
        staphers = [stapher1, stapher2]
        free_staphers = get_free_staphers(staphers, target_shift, [staphing])
        self.assertEqual(free_staphers, [stapher2])

class RecommendTests(TestCase):
# ============================================================================
# ---------------------   get_recommended_staphers  --------------------------
# ============================================================================

    def test_get_recommended_staphers_empty_staphers_returns_empty(self):
        result = get_recommended_staphers([], None, [], [], [])
        self.assertEqual(result, [])

    def test_get_recommended_staphers_returns_one_entry_per_stapher(self):
        stapher1 = Stapher(gender=0)
        stapher1.save()
        stapher2 = Stapher(gender=0)
        stapher2.save()
        shift = Shift(start=datetime.time(9), end=datetime.time(10))
        result = get_recommended_staphers([stapher1, stapher2], shift, [], [], [])
        self.assertEqual(len(result), 2)

    def test_get_recommended_staphers_each_entry_has_stapher_scores_wins(self):
        stapher1 = Stapher(gender=0)
        stapher1.save()
        shift = Shift(start=datetime.time(9), end=datetime.time(10))
        result = get_recommended_staphers([stapher1], shift, [], [], [])
        self.assertEqual(result[0][0], stapher1)
        self.assertIsInstance(result[0][1], list)
        self.assertIsInstance(result[0][2], list)


# ============================================================================
# ========================   AJAX VIEW TESTS   ================================
# ============================================================================

def _make_user_and_login(client):
    user = User.objects.create_user('testuser', '', 'testpass')
    client.login(username='testuser', password='testpass')
    return user


class BuildSchedulesViewTests(TestCase):
# ============================================================================
# --------------------   build_schedules (POST /building)   ------------------
# ============================================================================

    def setUp(self):
        cache.clear()
        self.client = Client()
        _make_user_and_login(self.client)
        self.shift_set = ShiftSet.objects.create(pk=1, title='Default')

    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse('schedules:building'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_no_active_schedule_shows_error(self):
        response = self.client.post(reverse('schedules:building'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Must select a schedule first')

    @patch('schedules.views.build_schedules_task')
    def test_active_schedule_renders_progress_template(self, mock_task):
        mock_task.delay.return_value.task_id = 'build-task-id'
        Schedule.objects.create(active=True, title='Test Schedule', shift_set=self.shift_set)
        response = self.client.post(reverse('schedules:building'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schedules/progress.html')

    @patch('schedules.views.build_schedules_task')
    def test_active_schedule_passes_task_id_to_template(self, mock_task):
        mock_task.delay.return_value.task_id = 'build-task-id'
        Schedule.objects.create(active=True, title='Test Schedule', shift_set=self.shift_set)
        response = self.client.post(reverse('schedules:building'))
        self.assertEqual(response.context['task_id'], 'build-task-id')

    @patch('schedules.views.build_schedules_task')
    def test_active_schedule_fires_celery_task(self, mock_task):
        mock_task.delay.return_value.task_id = 'build-task-id'
        schedule = Schedule.objects.create(active=True, title='Test Schedule', shift_set=self.shift_set)
        self.client.post(reverse('schedules:building'))
        mock_task.delay.assert_called_once_with(schedule.id)

    @patch('schedules.views.build_schedules_task')
    def test_eager_mode_redirects_to_redirect_view(self, mock_task):
        # Simulate task running synchronously: it deletes current_task_id before returning.
        def eager_side_effect(*args, **kwargs):
            cache.delete('current_task_id')
            result = MagicMock()
            result.task_id = 'eager-id'
            return result
        mock_task.delay.side_effect = eager_side_effect
        Schedule.objects.create(active=True, title='Test Schedule', shift_set=self.shift_set)
        response = self.client.post(reverse('schedules:building'))
        self.assertRedirects(response, reverse('schedules:redirect'), fetch_redirect_response=False)

    @patch('schedules.views.build_schedules_task')
    def test_already_running_task_skips_new_task(self, mock_task):
        # With a task already in flight, should not dispatch a second one.
        cache.set('current_task_id', 'existing-task-id', 3000)
        Schedule.objects.create(active=True, title='Test Schedule', shift_set=self.shift_set)
        self.client.post(reverse('schedules:building'))
        mock_task.delay.assert_not_called()


class GetRatioViewTests(TestCase):
# ============================================================================
# ---------------   get_ratio (GET /get_ratios) — Check Ratios   -------------
# ============================================================================

    def setUp(self):
        cache.clear()
        self.client = Client()
        _make_user_and_login(self.client)
        self.shift_set = ShiftSet.objects.create(pk=1, title='Default')

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('schedules:get-ratio'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_no_active_schedule_shows_error(self):
        response = self.client.get(reverse('schedules:get-ratio'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Must select a schedule first')

    @patch('schedules.views.find_ratios_task')
    def test_active_schedule_fires_celery_task(self, mock_task):
        mock_task.delay.return_value.task_id = 'ratio-task-id'
        schedule = Schedule.objects.create(active=True, title='Test Schedule', shift_set=self.shift_set)
        self.client.get(reverse('schedules:get-ratio'))
        mock_task.delay.assert_called_once_with(schedule.id, self.shift_set.id)

    @patch('schedules.views.find_ratios_task')
    def test_active_schedule_redirects_to_schedule(self, mock_task):
        mock_task.delay.return_value.task_id = 'ratio-task-id'
        Schedule.objects.create(active=True, title='Test Schedule', shift_set=self.shift_set)
        response = self.client.get(reverse('schedules:get-ratio'))
        self.assertRedirects(response, reverse('schedules:schedule'))

    @patch('schedules.views.find_ratios_task')
    def test_task_id_stored_in_session(self, mock_task):
        mock_task.delay.return_value.task_id = 'ratio-task-id'
        Schedule.objects.create(active=True, title='Test Schedule', shift_set=self.shift_set)
        self.client.get(reverse('schedules:get-ratio'))
        self.assertEqual(self.client.session['task_id'], 'ratio-task-id')

    @patch('schedules.views.find_ratios_task')
    def test_eager_mode_redirects_to_redirect_view(self, mock_task):
        def eager_side_effect(*args, **kwargs):
            cache.delete('current_task_id')
            result = MagicMock()
            result.task_id = 'eager-id'
            return result
        mock_task.delay.side_effect = eager_side_effect
        Schedule.objects.create(active=True, title='Test Schedule', shift_set=self.shift_set)
        response = self.client.get(reverse('schedules:get-ratio'))
        self.assertRedirects(response, reverse('schedules:redirect'), fetch_redirect_response=False)

    @patch('schedules.views.find_ratios_task')
    def test_already_running_task_skips_new_task(self, mock_task):
        cache.set('current_task_id', 'existing-task-id', 3000)
        Schedule.objects.create(active=True, title='Test Schedule', shift_set=self.shift_set)
        self.client.get(reverse('schedules:get-ratio'))
        mock_task.delay.assert_not_called()


class TrackStateViewTests(TestCase):
# ============================================================================
# --------   track_state (POST /track) — AJAX polling endpoint   -------------
# ============================================================================

    def setUp(self):
        cache.clear()
        self.client = Client()
        _make_user_and_login(self.client)

    def _ajax_post(self, data):
        return self.client.post(
            reverse('schedules:track'),
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

    def test_requires_login(self):
        self.client.logout()
        response = self._ajax_post({'task_id': 'some-id'})
        self.assertEqual(response.status_code, 302)

    def test_always_returns_json_content_type(self):
        response = self._ajax_post({'task_id': ''})
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_non_ajax_request_returns_error_string(self):
        # Without the XMLHttpRequest header the endpoint must return a clear
        # error string — not a 500 (which is what the removed is_ajax() caused).
        response = self.client.post(reverse('schedules:track'), {'task_id': 'x'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), 'This is not an ajax request')

    def test_ajax_with_empty_task_id_returns_error(self):
        response = self._ajax_post({'task_id': ''})
        self.assertEqual(json.loads(response.content), 'No task_id in the request')

    def test_ajax_with_missing_task_id_key_returns_error(self):
        response = self._ajax_post({})
        self.assertEqual(json.loads(response.content), 'No task_id in the request')

    @patch('schedules.views.app')
    def test_running_task_returns_progress_with_running_flag(self, mock_app):
        mock_result = MagicMock()
        mock_result.result = {'message': 'Placing Shifts', 'process_percent': 42}
        mock_result.state = 'PROGRESS'
        mock_result.ready.return_value = False
        mock_app.AsyncResult.return_value = mock_result

        response = self._ajax_post({'task_id': 'running-id'})
        data = json.loads(response.content)
        self.assertEqual(data['process_percent'], 42)
        self.assertEqual(data['message'], 'Placing Shifts')
        self.assertTrue(data['running'])

    @patch('schedules.views.app')
    def test_completed_task_returns_state_without_running_flag(self, mock_app):
        mock_result = MagicMock()
        mock_result.result = None
        mock_result.state = 'SUCCESS'
        mock_result.ready.return_value = True
        mock_app.AsyncResult.return_value = mock_result

        response = self._ajax_post({'task_id': 'done-id'})
        data = json.loads(response.content)
        self.assertNotIn('running', data if isinstance(data, dict) else {})

    @patch('schedules.views.app')
    def test_pending_task_returns_running_true(self, mock_app):
        mock_result = MagicMock()
        mock_result.result = None
        mock_result.state = 'PENDING'
        mock_result.ready.return_value = False
        mock_app.AsyncResult.return_value = mock_result

        response = self._ajax_post({'task_id': 'pending-id'})
        data = json.loads(response.content)
        self.assertIsInstance(data, dict)
        self.assertTrue(data['running'])
        self.assertEqual(data['process_percent'], 0)

    @patch('schedules.views.app')
    def test_failed_task_returns_json_not_500(self, mock_app):
        mock_result = MagicMock()
        mock_result.result = ValueError('worker died')
        mock_result.state = 'FAILURE'
        mock_result.ready.return_value = True
        mock_app.AsyncResult.return_value = mock_result

        response = self._ajax_post({'task_id': 'failed-id'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')


# ============================================================================
# =============   build_view (GET /schedules/) — schedule hub   ==============
# ============================================================================

class BuildViewTests(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        _make_user_and_login(self.client)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('schedules:schedule'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_no_task_renders_schedule_template(self):
        response = self.client.get(reverse('schedules:schedule'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schedules/schedule.html')

    def test_task_in_cache_renders_progress_template(self):
        cache.set('current_task_id', 'some-task-id', 3000)
        response = self.client.get(reverse('schedules:schedule'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schedules/progress.html')

    def test_task_in_cache_passes_task_id_to_template(self):
        cache.set('current_task_id', 'some-task-id', 3000)
        response = self.client.get(reverse('schedules:schedule'))
        self.assertEqual(response.context['task_id'], 'some-task-id')

    def test_always_clears_no_redirect_from_cache(self):
        cache.set('no_redirect', True, None)
        self.client.get(reverse('schedules:schedule'))
        self.assertIsNone(cache.get('no_redirect'))


# ============================================================================
# =============   redirect (GET /schedules/redirect) — post-task   ===========
# ============================================================================

class RedirectViewTests(TestCase):

    def setUp(self):
        cache.clear()
        self.client = Client()
        _make_user_and_login(self.client)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('schedules:redirect'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_no_redirect_value_goes_to_schedule(self):
        response = self.client.get(reverse('schedules:redirect'))
        self.assertRedirects(response, reverse('schedules:schedule'), fetch_redirect_response=False)

    def test_ratio_redirect_goes_to_ratio_week(self):
        cache.set('redirect_value', RATIO_REDIRECT, 300)
        response = self.client.get(reverse('schedules:redirect'))
        self.assertRedirects(response, reverse('schedules:ratio-week'), fetch_redirect_response=False)

    def test_recommendation_redirect_goes_to_recommendation(self):
        cache.set('redirect_value', RECOMMENDATION_REDIRECT, 300)
        response = self.client.get(reverse('schedules:redirect'))
        self.assertRedirects(response, reverse('schedules:recommendation'), fetch_redirect_response=False)

    def test_special_shift_redirect_goes_to_special_results(self):
        cache.set('redirect_value', SPECIAL_SHIFT_REDIRECT, 300)
        response = self.client.get(reverse('schedules:redirect'))
        self.assertRedirects(response, reverse('schedules:special-results'), fetch_redirect_response=False)


# ============================================================================
# ========================   ANALYTICS TESTS   ================================
# ============================================================================

class AnalyticsTests(TestCase):

    def test_get_hours_from_timedelta_zero(self):
        self.assertEqual(get_hours_from_timedelta(datetime.timedelta(0)), 0)

    def test_get_hours_from_timedelta_one_hour(self):
        self.assertEqual(get_hours_from_timedelta(datetime.timedelta(hours=1)), 1.0)

    def test_get_hours_from_timedelta_one_day(self):
        self.assertEqual(get_hours_from_timedelta(datetime.timedelta(days=1)), 24.0)

    def test_get_hours_from_timedelta_half_hour(self):
        self.assertEqual(get_hours_from_timedelta(datetime.timedelta(minutes=30)), 0.5)

    def test_get_td_from_time_midnight(self):
        self.assertEqual(get_td_from_time(datetime.time(0, 0)), datetime.timedelta(0))

    def test_get_td_from_time_noon(self):
        self.assertEqual(get_td_from_time(datetime.time(12, 0)), datetime.timedelta(hours=12))

    def test_get_td_from_time_with_minutes(self):
        self.assertEqual(get_td_from_time(datetime.time(9, 30)), datetime.timedelta(hours=9, minutes=30))

    def test_get_hours_between_times_one_hour(self):
        self.assertEqual(get_hours_between_times(datetime.time(9, 0), datetime.time(10, 0)), 1.0)

    def test_get_hours_between_times_half_hour(self):
        self.assertEqual(get_hours_between_times(datetime.time(9, 0), datetime.time(9, 30)), 0.5)

    def test_get_hours_between_times_two_hours(self):
        self.assertEqual(get_hours_between_times(datetime.time(8, 0), datetime.time(10, 0)), 2.0)

    def test_get_readable_time_9am(self):
        self.assertEqual(get_readable_time(datetime.time(9, 0)), '9am')

    def test_get_readable_time_2pm(self):
        self.assertEqual(get_readable_time(datetime.time(14, 0)), '2pm')

    def test_get_readable_time_noon(self):
        self.assertEqual(get_readable_time(datetime.time(12, 0)), '12pm')

    def test_get_readable_time_with_minutes(self):
        self.assertEqual(get_readable_time(datetime.time(9, 30)), '9:30am')

    def test_get_str_from_td_one_hour_contains_1(self):
        self.assertIn('1', get_str_from_td(datetime.timedelta(hours=1)))

    def test_get_str_from_td_noon_contains_12(self):
        self.assertIn('12', get_str_from_td(datetime.timedelta(hours=12)))

    def test_get_average_window_no_gaps(self):
        shifts_by_day = {day: [] for day in range(7)}
        self.assertEqual(get_average_window_between_shifts(None, None, None, shifts_by_day, None, None), [24])

    def test_get_average_window_one_hour_gap(self):
        shift1 = Shift(start=datetime.time(9, 0), end=datetime.time(10, 0))
        shift2 = Shift(start=datetime.time(11, 0), end=datetime.time(12, 0))
        shifts_by_day = {day: [] for day in range(7)}
        shifts_by_day[0] = [shift1, shift2]
        self.assertEqual(get_average_window_between_shifts(None, None, None, shifts_by_day, None, None), [1.0])

    def test_get_average_window_zero_gap_excluded(self):
        shift1 = Shift(start=datetime.time(9, 0), end=datetime.time(10, 0))
        shift2 = Shift(start=datetime.time(10, 0), end=datetime.time(11, 0))
        shifts_by_day = {day: [] for day in range(7)}
        shifts_by_day[0] = [shift1, shift2]
        self.assertEqual(get_average_window_between_shifts(None, None, None, shifts_by_day, None, None), [24])

    def test_get_people_not_worked_with_no_staphings(self):
        stapher = Stapher(gender=0)
        stapher.save()
        other = Stapher(gender=0)
        other.save()
        result = get_people_not_worked_with(stapher, [stapher, other], [], {}, None, None)
        self.assertEqual(result[0], 1)

    def test_get_people_not_worked_with_all_alone(self):
        stapher = Stapher(gender=0)
        stapher.save()
        result = get_people_not_worked_with(stapher, [stapher], [], {}, None, None)
        self.assertEqual(result[0], 0)

    def test_get_people_not_worked_with_worked_together(self):
        stapher = Stapher(gender=0)
        stapher.save()
        other = Stapher(gender=0)
        other.save()
        shift = Shift(start=datetime.time(9), end=datetime.time(10))
        schedule = Schedule()
        staphings = [
            Staphing(stapher=stapher, shift=shift, schedule=schedule),
            Staphing(stapher=other, shift=shift, schedule=schedule),
        ]
        result = get_people_not_worked_with(stapher, [stapher, other], staphings, {}, None, None)
        self.assertEqual(result[0], 0)


# ============================================================================
# ========================   HELPERS TESTS   ==================================
# ============================================================================

class HelpersTests(TestCase):

    def test_get_min_zero_minutes(self):
        self.assertEqual(get_min(datetime.time(9, 0)), 0)

    def test_get_min_15_minutes(self):
        self.assertEqual(get_min(datetime.time(9, 15)), 0.25)

    def test_get_min_30_minutes(self):
        self.assertEqual(get_min(datetime.time(9, 30)), 0.5)

    def test_get_min_45_minutes(self):
        self.assertEqual(get_min(datetime.time(9, 45)), 0.75)

    def test_get_time_str_whole_hour(self):
        self.assertEqual(get_time_str(datetime.time(9, 0)), '9')

    def test_get_time_str_half_hour(self):
        self.assertEqual(get_time_str(datetime.time(9, 30)), '9.5')

    def test_get_time_str_quarter_hour(self):
        self.assertEqual(get_time_str(datetime.time(9, 15)), '9.25')

    def test_get_span_from_time_one_hour(self):
        self.assertEqual(get_span_from_time(datetime.time(9, 0), datetime.time(10, 0)), 12)

    def test_get_span_from_time_30_minutes(self):
        self.assertEqual(get_span_from_time(datetime.time(9, 0), datetime.time(9, 30)), 6)

    def test_get_span_from_time_two_hours(self):
        self.assertEqual(get_span_from_time(datetime.time(9, 0), datetime.time(11, 0)), 24)

    def test_get_max_ratio_single_entry(self):
        ratios = [[[2, 4], 'dummy']]
        self.assertAlmostEqual(get_max_ratio(ratios), 0.5)

    def test_get_max_ratio_picks_highest(self):
        ratios = [[[1, 2], 'dummy'], [[3, 2], 'dummy']]
        self.assertAlmostEqual(get_max_ratio(ratios), 1.5)

    def test_get_max_ratio_zero_denominator(self):
        ratios = [[[5, 0], 'dummy']]
        self.assertEqual(get_max_ratio(ratios), 6)

    def test_get_max_ratio_equal_ratio(self):
        ratios = [[[2, 2], 'dummy']]
        self.assertAlmostEqual(get_max_ratio(ratios), 1.0)


# ============================================================================
# =====================   SORT UNIT TESTS   ===================================
# ============================================================================

class SortUnitTests(TestCase):

    def test_get_seconds_from_time_midnight(self):
        self.assertEqual(get_seconds_from_time(datetime.time(0, 0)), 0)

    def test_get_seconds_from_time_one_hour(self):
        self.assertEqual(get_seconds_from_time(datetime.time(1, 0)), 3600)

    def test_get_seconds_from_time_with_minutes(self):
        self.assertEqual(get_seconds_from_time(datetime.time(1, 30)), 5400)

    def test_get_seconds_from_time_noon(self):
        self.assertEqual(get_seconds_from_time(datetime.time(12, 0)), 43200)

    def test_get_seconds_from_day_and_time_sunday_midnight(self):
        self.assertEqual(get_seconds_from_day_and_time(0, datetime.time(0, 0)), 0)

    def test_get_seconds_from_day_and_time_monday_midnight(self):
        self.assertEqual(get_seconds_from_day_and_time(1, datetime.time(0, 0)), 86400)

    def test_get_seconds_from_day_and_time_with_time(self):
        self.assertEqual(get_seconds_from_day_and_time(1, datetime.time(12, 0)), 86400 + 43200)

    def test_get_seconds_from_day_and_time_saturday(self):
        self.assertEqual(get_seconds_from_day_and_time(6, datetime.time(0, 0)), 6 * 86400)

    def test_get_ordered_times_single_shift(self):
        shift = Shift(day=0, start=datetime.time(9), end=datetime.time(10))
        result = get_ordered_start_and_end_times_by_day([shift])
        self.assertEqual(result[0], [datetime.time(9), datetime.time(10)])

    def test_get_ordered_times_two_shifts_same_day(self):
        shift1 = Shift(day=0, start=datetime.time(9), end=datetime.time(10))
        shift2 = Shift(day=0, start=datetime.time(11), end=datetime.time(12))
        result = get_ordered_start_and_end_times_by_day([shift1, shift2])
        self.assertEqual(result[0], [datetime.time(9), datetime.time(10), datetime.time(11), datetime.time(12)])

    def test_get_ordered_times_two_different_days(self):
        shift1 = Shift(day=0, start=datetime.time(9), end=datetime.time(10))
        shift2 = Shift(day=1, start=datetime.time(11), end=datetime.time(12))
        result = get_ordered_start_and_end_times_by_day([shift1, shift2])
        self.assertIn(0, result)
        self.assertIn(1, result)
        self.assertNotIn(2, result)

    def test_get_ordered_times_deduplicates_same_time(self):
        shift1 = Shift(day=0, start=datetime.time(9), end=datetime.time(10))
        shift2 = Shift(day=0, start=datetime.time(9), end=datetime.time(11))
        result = get_ordered_start_and_end_times_by_day([shift1, shift2])
        self.assertEqual(result[0].count(datetime.time(9)), 1)


# ============================================================================
# ======================   BUILD UNIT TESTS   =================================
# ============================================================================

class BuildUnitTests(TestCase):

    def test_do_ties_exist_no_tie(self):
        recs = [
            [None, None, [True, True]],
            [None, None, [True, False]],
        ]
        self.assertFalse(do_ties_exist(recs, 1))

    def test_do_ties_exist_with_tie(self):
        recs = [
            [None, None, [True, False]],
            [None, None, [True, False]],
        ]
        self.assertTrue(do_ties_exist(recs, 1))

    def test_highest_ranked_win_at_index_zero(self):
        self.assertEqual(highest_ranked_win([None, None, [True, False, False]]), 0)

    def test_highest_ranked_win_at_index_one(self):
        self.assertEqual(highest_ranked_win([None, None, [False, True, False]]), 1)

    def test_highest_ranked_win_no_wins_returns_length(self):
        self.assertEqual(highest_ranked_win([None, None, [False, False]]), 2)

    def test_get_free_staphers_all_free_with_no_staphings(self):
        stapher1 = Stapher(gender=0)
        stapher1.save()
        stapher2 = Stapher(gender=0)
        stapher2.save()
        shift = Shift(start=datetime.time(9), end=datetime.time(10))
        result = get_free_staphers([stapher1, stapher2], shift, [])
        self.assertEqual(len(result), 2)

    def test_get_free_staphers_one_busy(self):
        stapher1 = Stapher(gender=0)
        stapher1.save()
        stapher2 = Stapher(gender=0)
        stapher2.save()
        busy_shift = Shift(start=datetime.time(9), end=datetime.time(10))
        target_shift = Shift(start=datetime.time(9), end=datetime.time(10))
        schedule = Schedule()
        staphing = Staphing(stapher=stapher1, shift=busy_shift, schedule=schedule)
        result = get_free_staphers([stapher1, stapher2], target_shift, [staphing])
        self.assertEqual(result, [stapher2])

    def test_get_free_staphers_non_overlapping_is_free(self):
        stapher = Stapher(gender=0)
        stapher.save()
        morning_shift = Shift(start=datetime.time(9), end=datetime.time(10))
        afternoon_shift = Shift(start=datetime.time(14), end=datetime.time(15))
        schedule = Schedule()
        staphing = Staphing(stapher=stapher, shift=morning_shift, schedule=schedule)
        result = get_free_staphers([stapher], afternoon_shift, [staphing])
        self.assertEqual(result, [stapher])



















