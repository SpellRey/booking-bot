"""Розрахунок доступних днів і вільного часу. Чисті функції без Telegram і бази."""

from __future__ import annotations

from datetime import date, datetime, timedelta

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
MONTHS = [
    "січня", "лютого", "березня", "квітня", "травня", "червня",
    "липня", "серпня", "вересня", "жовтня", "листопада", "грудня",
]


def available_days(today: date, days_ahead: int, days_off: set[int]) -> list[date]:
    """Робочі дні від сьогодні на days_ahead днів уперед."""
    days = (today + timedelta(days=offset) for offset in range(days_ahead))
    return [day for day in days if day.weekday() not in days_off]


def all_slots(work_start: int, work_end: int) -> list[str]:
    """Усі години запису за день: ['10:00', '11:00', ...]."""
    return [f"{hour:02d}:00" for hour in range(work_start, work_end)]


def free_slots(day: date, taken: set[str], now: datetime, work_start: int, work_end: int) -> list[str]:
    """Вільний час на день: без зайнятих годин і без тих, що сьогодні вже минули."""
    slots = [slot for slot in all_slots(work_start, work_end) if slot not in taken]
    if day == now.date():
        current = now.strftime("%H:%M")
        slots = [slot for slot in slots if slot > current]
    return slots


def format_day(day: date) -> str:
    """date(2026, 11, 14) -> 'Сб, 14 листопада'"""
    return f"{WEEKDAYS[day.weekday()]}, {day.day} {MONTHS[day.month - 1]}"
