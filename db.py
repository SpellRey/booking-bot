"""Зберігання записів у SQLite."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class Booking:
    id: int
    user_id: int
    user_name: str
    service: str
    day: str   # 'YYYY-MM-DD'
    time: str  # 'HH:MM'


class Database:
    def __init__(self, path: str):
        self.path = path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Відкриває з'єднання, зберігає зміни і гарантовано закриває його."""
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bookings (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id   INTEGER NOT NULL,
                    user_name TEXT    NOT NULL,
                    service   TEXT    NOT NULL,
                    day       TEXT    NOT NULL,
                    time      TEXT    NOT NULL,
                    UNIQUE (day, time)  -- на один час тільки один запис
                )
                """
            )

    def add_booking(self, user_id: int, user_name: str, service: str, day: str, time: str) -> int | None:
        """Створює запис і повертає його номер. Якщо час уже зайнятий, повертає None."""
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "INSERT INTO bookings (user_id, user_name, service, day, time) VALUES (?, ?, ?, ?, ?)",
                    (user_id, user_name, service, day, time),
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def taken_times(self, day: str) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT time FROM bookings WHERE day = ?", (day,)).fetchall()
        return {row["time"] for row in rows}

    def user_bookings(self, user_id: int, from_day: str) -> list[Booking]:
        """Записи клієнта, починаючи з from_day, від найближчого."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM bookings WHERE user_id = ? AND day >= ? ORDER BY day, time",
                (user_id, from_day),
            ).fetchall()
        return [Booking(**dict(row)) for row in rows]

    def bookings_for_day(self, day: str) -> list[Booking]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM bookings WHERE day = ? ORDER BY time", (day,)).fetchall()
        return [Booking(**dict(row)) for row in rows]

    def get_booking(self, booking_id: int) -> Booking | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        return Booking(**dict(row)) if row else None

    def cancel_booking(self, booking_id: int, user_id: int) -> bool:
        """Скасовує запис. Клієнт може скасувати тільки свій; повертає True, якщо скасовано."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM bookings WHERE id = ? AND user_id = ?", (booking_id, user_id))
            return cursor.rowcount > 0
