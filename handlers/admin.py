"""Команди адміністратора: розклад на день. Працюють тільки для ADMIN_ID з .env."""

from __future__ import annotations

from datetime import date, timedelta

from aiogram import Router, html
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from config import Config
from db import Database
from handlers.booking import now_local
from schedule import format_day

router = Router()


def day_schedule(db: Database, day: date) -> str:
    bookings = db.bookings_for_day(day.isoformat())
    title = f"📅 <b>{format_day(day)}</b>"
    if not bookings:
        return f"{title}\n\nЗаписів немає."
    lines = [
        f"{b.time} · {html.quote(b.service)} · {html.link(html.quote(b.user_name), f'tg://user?id={b.user_id}')}"
        for b in bookings
    ]
    return f"{title}\n\n" + "\n".join(lines) + f"\n\nВсього: {len(bookings)}"


def is_admin(message: Message, config: Config) -> bool:
    return bool(config.admin_id) and message.from_user.id == config.admin_id


@router.message(Command("today"))
async def today(message: Message, db: Database, config: Config) -> None:
    if is_admin(message, config):
        await message.answer(day_schedule(db, now_local().date()))


@router.message(Command("tomorrow"))
async def tomorrow(message: Message, db: Database, config: Config) -> None:
    if is_admin(message, config):
        await message.answer(day_schedule(db, now_local().date() + timedelta(days=1)))


@router.message(Command("day"))
async def any_day(message: Message, command: CommandObject, db: Database, config: Config) -> None:
    """Розклад на дату: /day 2026-11-20"""
    if not is_admin(message, config):
        return
    try:
        day = date.fromisoformat((command.args or "").strip())
    except ValueError:
        await message.answer("Вкажіть дату у форматі РРРР-ММ-ДД, наприклад: /day 2026-11-20")
        return
    await message.answer(day_schedule(db, day))
