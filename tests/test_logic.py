"""Тести розкладу і бази. Не потребують Telegram і токена."""

import sys
from datetime import date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import Database  # noqa: E402
from schedule import all_slots, available_days, format_day, free_slots  # noqa: E402


@pytest.fixture
def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.init()
    return database


# --- Розклад ---------------------------------------------------------------


def test_available_days_skip_sunday():
    friday = date(2026, 11, 13)
    days = available_days(friday, days_ahead=7, days_off={6})
    assert days[0] == friday
    assert date(2026, 11, 15) not in days  # неділя
    assert len(days) == 6


def test_all_slots():
    assert all_slots(10, 13) == ["10:00", "11:00", "12:00"]


def test_free_slots_exclude_taken():
    day = date(2026, 11, 14)
    now = datetime(2026, 11, 13, 15, 0)
    assert free_slots(day, {"11:00"}, now, 10, 13) == ["10:00", "12:00"]


def test_free_slots_today_exclude_past():
    today = date(2026, 11, 13)
    now = datetime(2026, 11, 13, 11, 30)
    assert free_slots(today, set(), now, 10, 14) == ["12:00", "13:00"]


def test_format_day():
    assert format_day(date(2026, 11, 14)) == "Сб, 14 листопада"


# --- База ------------------------------------------------------------------


def test_add_and_read_booking(db):
    booking_id = db.add_booking(1, "Павло", "Стрижка", "2026-11-14", "10:00")
    booking = db.get_booking(booking_id)
    assert booking.user_name == "Павло"
    assert db.taken_times("2026-11-14") == {"10:00"}


def test_same_slot_cannot_be_booked_twice(db):
    assert db.add_booking(1, "Павло", "Стрижка", "2026-11-14", "10:00") is not None
    assert db.add_booking(2, "Ігор", "Борода", "2026-11-14", "10:00") is None


def test_user_bookings_sorted_and_without_past(db):
    db.add_booking(1, "Павло", "Стрижка", "2026-11-20", "12:00")
    db.add_booking(1, "Павло", "Стрижка", "2026-11-14", "15:00")
    db.add_booking(1, "Павло", "Стрижка", "2026-11-01", "10:00")  # уже минув
    db.add_booking(2, "Ігор", "Борода", "2026-11-14", "10:00")  # чужий

    bookings = db.user_bookings(1, from_day="2026-11-13")
    assert [(b.day, b.time) for b in bookings] == [("2026-11-14", "15:00"), ("2026-11-20", "12:00")]


def test_cancel_only_own_booking(db):
    booking_id = db.add_booking(1, "Павло", "Стрижка", "2026-11-14", "10:00")
    assert db.cancel_booking(booking_id, user_id=2) is False  # чужий не може
    assert db.cancel_booking(booking_id, user_id=1) is True
    assert db.get_booking(booking_id) is None
    # після скасування час знову вільний
    assert db.add_booking(2, "Ігор", "Борода", "2026-11-14", "10:00") is not None


def test_bookings_for_day_sorted(db):
    db.add_booking(1, "Павло", "Стрижка", "2026-11-14", "15:00")
    db.add_booking(2, "Ігор", "Борода", "2026-11-14", "10:00")
    assert [b.time for b in db.bookings_for_day("2026-11-14")] == ["10:00", "15:00"]
