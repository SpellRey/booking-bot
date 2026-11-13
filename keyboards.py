"""Клавіатури бота: головне меню і кнопки під повідомленнями."""

from __future__ import annotations

from datetime import date

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import SERVICES
from db import Booking
from schedule import format_day

BTN_BOOK = "✂️ Записатися"
BTN_MY = "📋 Мої записи"
BTN_PRICES = "💈 Послуги та ціни"
BTN_CONTACTS = "📍 Контакти"

# Дані кнопок мають вигляд "дія:значення", наприклад "svc:2" або "time:14:00"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_BOOK), KeyboardButton(text=BTN_MY)],
            [KeyboardButton(text=BTN_PRICES), KeyboardButton(text=BTN_CONTACTS)],
        ],
        resize_keyboard=True,
    )


def services_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for service in SERVICES:
        builder.button(text=f"{service.name} · {service.price} грн", callback_data=f"svc:{service.id}")
    builder.button(text="✖️ Скасувати", callback_data="stop")
    builder.adjust(1)
    return builder.as_markup()


def days_kb(days: list[date]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for day in days:
        builder.button(text=format_day(day), callback_data=f"day:{day.isoformat()}")
    builder.button(text="⬅️ Назад", callback_data="back:services")
    builder.adjust(1)
    return builder.as_markup()


def times_kb(slots: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(text=slot, callback_data=f"time:{slot}")
    builder.adjust(3)
    back = InlineKeyboardBuilder()
    back.button(text="⬅️ Назад", callback_data="back:days")
    builder.attach(back)
    return builder.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Підтвердити", callback_data="confirm")
    builder.button(text="⬅️ Назад", callback_data="back:times")
    builder.button(text="✖️ Скасувати", callback_data="stop")
    builder.adjust(1)
    return builder.as_markup()


def cancel_booking_kb(booking: Booking) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Скасувати запис", callback_data=f"cancel:{booking.id}")
    return builder.as_markup()
