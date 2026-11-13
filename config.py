"""Налаштування бота: секрети з файлу .env і параметри салону."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Service:
    id: int
    name: str
    price: int  # грн
    minutes: int


# --- Те, що змінюється під конкретного замовника ---------------------------

SALON_NAME = "Barber Demo"
CONTACTS = "📍 м. Львів, вул. Прикладна, 1\n🕙 Пн–Сб, 10:00–19:00"

SERVICES = [
    Service(1, "Чоловіча стрижка", 400, 45),
    Service(2, "Стрижка бороди", 250, 30),
    Service(3, "Стрижка + борода", 600, 60),
    Service(4, "Дитяча стрижка", 300, 30),
]

WORK_START = 10        # перший запис о 10:00
WORK_END = 19          # останній запис о 18:00
DAYS_AHEAD = 7         # на скільки днів уперед можна записатися
DAYS_OFF = {6}         # вихідні: 0 = понеділок ... 6 = неділя
MAX_ACTIVE_BOOKINGS = 3  # скільки записів одночасно може мати один клієнт
TIMEZONE = "Europe/Kyiv"

# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Config:
    token: str
    admin_id: int
    db_path: str


def load_config() -> Config:
    """Читає .env. Якщо токена немає, зупиняє запуск зі зрозумілим повідомленням."""
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Не знайдено BOT_TOKEN. Скопіюй .env.example у .env і встав токен від @BotFather.")

    admin_raw = os.getenv("ADMIN_ID", "0").strip() or "0"
    if not admin_raw.isdigit():
        raise SystemExit("ADMIN_ID у файлі .env має бути числом (твій Telegram ID).")

    return Config(token=token, admin_id=int(admin_raw), db_path=os.getenv("DB_PATH", "bookings.db"))


def get_service(service_id: int) -> Service | None:
    return next((s for s in SERVICES if s.id == service_id), None)
