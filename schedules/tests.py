import datetime
from django.conf import settings
from django.test import TestCase

from .build import get_free_staphers
from .models import Stapher, Shift, Qualification, Schedule, Staphing, Settings, Parameter
from .sort import get_qual_and_shifts_dicts, get_stapher_dict, get_sorted_shifts
from .recommend import get_recommended_staphers

class StapherModelTests(TestCase):
# ============================================================================
# -----------------------   STAPHER IS_QUALIFIED   --------------------------
# ============================================================================
    def test_is_qualified_stapher_has_same_qualifications_for_shift(self):
        # Make sure is_qualified is working when the shift and stapher have the same qualifications
        stapher = Stapher()
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
        stapher = Stapher()
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
        stapher = Stapher()
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
        stapher = Stapher()
        stapher.save()
        shift = Shift()
        shift.save()
        q1 = Qualification(title = 'one')
        q1.save()
        shift.qualifications.add(q1)
        self.assertFalse(stapher.is_qualified(shift))

    def test_is_qualified_shift_has_no_qualifications(self):
        # Make sure is_qualified is working when the shift and stapher have the same qualifications
        stapher = Stapher()
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
        stapher = Stapher()
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
        stapher = Stapher()
        stapher.save()
        shift1 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 10))
        shift1.save()
        schedule = Schedule()
        schedule.save()
        staphing = Staphing(stapher = stapher, shift = shift1, schedule = schedule)
        self.assertFalse(stapher.is_free([staphing], shift1))


    def test_is_free_stapher_has_no_shifts(self):
        # Make sure is_free is working when the stapher has no shifts
        stapher = Stapher()
        shift1 = Shift(start = datetime.time(hour = 9), end = datetime.time(hour = 10))
        self.assertTrue(stapher.is_free([], shift1))

    def test_is_free_stapher_is_free(self):
        # Make sure is_free is working when the stapher has a shift that doesn't overlap scheduled
        stapher = Stapher()
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
        stapher = Stapher()
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
        stapher = Stapher()
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
        stapher = Stapher()
        self.assertEquals(stapher.hours_in_day([], 0).seconds, 0)

    def test_hours_in_day_one_hour_shifts(self):
        stapher = Stapher()
        shift = Shift()
        schedule = Schedule()
        staphing = Staphing(stapher = stapher, shift = shift, schedule = schedule)
        seconds_in_hour = 60 * 60
        self.assertEquals(stapher.hours_in_day([staphing], 0).seconds, seconds_in_hour)

    def test_hours_in_day_two_one_hour_shifts(self):
        stapher = Stapher()
        shift1 = Shift()
        shift2 = Shift()
        schedule = Schedule()
        staphing1 = Staphing(stapher = stapher, shift = shift1, schedule = schedule)
        staphing2 = Staphing(stapher = stapher, shift = shift2, schedule = schedule)
        seconds_in_hour = 60 * 60
        self.assertEquals(stapher.hours_in_day([staphing1, staphing2], 0).seconds, seconds_in_hour * 2)

    def test_hours_in_day_two_one_hour_shifts_different_days(self):
        stapher = Stapher()
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
        stapher = Stapher()
        self.assertEquals(stapher.total_hours([]).seconds, 0)

    def test_total_hours_one_hour_shifts(self):
        stapher = Stapher()
        shift = Shift()
        schedule = Schedule()
        staphing = Staphing(stapher = stapher, shift = shift, schedule = schedule)
        seconds_in_hour = 60 * 60
        self.assertEquals(stapher.total_hours([staphing]).seconds, seconds_in_hour)

    def test_total_hours_two_one_hour_shifts(self):
        stapher = Stapher()
        shift1 = Shift()
        shift2 = Shift()
        schedule = Schedule()
        staphing1 = Staphing(stapher = stapher, shift = shift1, schedule = schedule)
        staphing2 = Staphing(stapher = stapher, shift = shift2, schedule = schedule)
        seconds_in_hour = 60 * 60
        self.assertEquals(stapher.total_hours([staphing1, staphing2]).seconds, seconds_in_hour * 2)

    def test_total_hours_two_one_hour_shifts_different_days(self):
        stapher = Stapher()
        shift1 = Shift()
        shift2 = Shift(day=1)
        schedule = Schedule()
        staphing1 = Staphing(stapher = stapher, shift = shift1, schedule = schedule)
        staphing2 = Staphing(stapher = stapher, shift = shift2, schedule = schedule)
        seconds_in_hour = 60 * 60
        self.assertEquals(stapher.total_hours([staphing1, staphing2]).seconds, seconds_in_hour * 2)

    def test_total_hours_three_one_hour_shifts_different_days(self):
        stapher = Stapher()
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
        stapher = Stapher()
        stapher.save()
        schedule = Schedule()
        schedule.save()
        staphing = Staphing(shift = shift, stapher = stapher, schedule = schedule)
        self.assertTrue(shift.is_covered([staphing]))

    def test_is_covered_shift_that_needs_three_is_covered(self):
        # Test to make sure is_covered is working when shift that needs 3 workers has 3 workers
        shift = Shift(workers_needed = 3)
        shift.save()
        stapher1 = Stapher()
        stapher1.save()
        stapher2 = Stapher()
        stapher2.save()
        stapher3 = Stapher()
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
        stapher1 = Stapher()
        stapher1.save()
        stapher2 = Stapher()
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
        stapher = Stapher()
        schedule = Schedule()
        shift.save()
        stapher.save()
        schedule.save()
        staphing = Staphing(stapher = stapher, shift = shift, schedule = schedule)
        self.assertTrue(shift.left_to_cover([staphing]) == 0)

    def test_left_to_cover_partially_covered(self):
        shift = Shift(workers_needed = 2)
        stapher = Stapher()
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
        'flags.json',
        'qualifications.json',
        'staphers.json',
        'shifts.json'
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

    def test_get_sorted_shifts_are_sorted(self):
        shifts_are_sorted = True
        sorted_shifts = get_sorted_shifts()
        last_ratio = sorted_shifts[0][0]
        for shift in sorted_shifts:
            ratio = shift[0]
            if last_ratio < ratio:
                shifts_are_sorted = False
                break
            last_ratio = ratio
        self.assertTrue(shifts_are_sorted)

class BuildTests(TestCase):
# ============================================================================
# ------------------------   get_free_staphers  ------------------------------
# ============================================================================
    
    def test_get_free_staphers_one_stapher_free(self):
        stapher1 = Stapher()
        stapher1.save()
        stapher2 = Stapher()
        stapher2.save()
        shift = Shift()
        shift.save()
        schedule = Schedule()
        schedule.save()
        # add_shift(stapher1, shift, schedule)
        staphers = [stapher1, stapher2]
        free_staphers = get_free_staphers(staphers, shift, schedule)
        self.assertEqual(free_staphers, [stapher2])

class RecommendTests(TestCase):
# ============================================================================
# ---------------------   get_recommended_staphers  --------------------------
# ============================================================================

    def test_get_recommended_staphers_test(self):
        stapher1 = Stapher()
        stapher1.save()
        stapher2 = Stapher()
        stapher2.save()
        shift = Shift()
        shift.save()
        schedule = Schedule()
        schedule.save()
        staphers = [stapher1, stapher2]
        get_recommended_staphers(staphers, shift, schedule)



















