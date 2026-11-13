"""Запис клієнта крок за кроком: послуга -> день -> час -> підтвердження."""

from __future__ import annotations

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router, html
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from config import (
    DAYS_AHEAD,
    DAYS_OFF,
    MAX_ACTIVE_BOOKINGS,
    TIMEZONE,
    WORK_END,
    WORK_START,
    Config,
    get_service,
)
from db import Booking, Database
from schedule import available_days, format_day, free_slots

router = Router()
log = logging.getLogger(__name__)


class BookingFlow(StatesGroup):
    """Кроки запису. Бот пам'ятає, на якому кроці зараз кожен клієнт."""

    service = State()
    day = State()
    time = State()
    confirm = State()


def now_local() -> datetime:
    """Поточний час салону (без часового поясу, щоб порівнювати з годинами запису)."""
    return datetime.now(ZoneInfo(TIMEZONE)).replace(tzinfo=None)


def days_for_booking() -> list[date]:
    return available_days(now_local().date(), DAYS_AHEAD, DAYS_OFF)


def describe(booking: Booking) -> str:
    day = format_day(date.fromisoformat(booking.day))
    return f"<b>{day}, {booking.time}</b>\n{html.quote(booking.service)}"


async def notify_admin(bot: Bot, config: Config, text: str) -> None:
    """Пише адміну. Якщо не вдалося (адмін не запускав бота), запис усе одно лишається."""
    if not config.admin_id:
        return
    try:
        await bot.send_message(config.admin_id, text)
    except TelegramAPIError as error:
        log.warning("Не вдалося написати адміну: %s", error)


# --- Крок 1: вибір послуги --------------------------------------------------


@router.message(F.text == kb.BTN_BOOK)
async def start_booking(message: Message, state: FSMContext, db: Database) -> None:
    active = db.user_bookings(message.from_user.id, now_local().date().isoformat())
    if len(active) >= MAX_ACTIVE_BOOKINGS:
        await message.answer(
            f"У вас уже є {len(active)} активних записів. Скасуйте один у «{kb.BTN_MY}», щоб записатися ще."
        )
        return

    await state.set_state(BookingFlow.service)
    await message.answer("Оберіть послугу:", reply_markup=kb.services_kb())


# --- Крок 2: вибір дня ------------------------------------------------------


@router.callback_query(BookingFlow.service, F.data.startswith("svc:"))
async def choose_service(callback: CallbackQuery, state: FSMContext) -> None:
    service = get_service(int(callback.data.split(":")[1]))
    if service is None:
        await callback.answer("Такої послуги вже немає", show_alert=True)
        return

    await state.update_data(service=service.name, price=service.price)
    await state.set_state(BookingFlow.day)
    await callback.message.edit_text(
        f"Послуга: <b>{html.quote(service.name)}</b>\n\nОберіть день:",
        reply_markup=kb.days_kb(days_for_booking()),
    )
    await callback.answer()


# --- Крок 3: вибір часу -----------------------------------------------------


@router.callback_query(BookingFlow.day, F.data.startswith("day:"))
async def choose_day(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    day = date.fromisoformat(callback.data.split(":", 1)[1])
    if day not in days_for_booking():
        await callback.answer("На цей день запис уже недоступний", show_alert=True)
        return

    slots = free_slots(day, db.taken_times(day.isoformat()), now_local(), WORK_START, WORK_END)
    if not slots:
        await callback.answer("На цей день вільного часу немає, оберіть інший", show_alert=True)
        return

    await state.update_data(day=day.isoformat())
    await state.set_state(BookingFlow.time)
    await callback.message.edit_text(
        f"День: <b>{format_day(day)}</b>\n\nОберіть час:", reply_markup=kb.times_kb(slots)
    )
    await callback.answer()


# --- Крок 4: підтвердження --------------------------------------------------


@router.callback_query(BookingFlow.time, F.data.startswith("time:"))
async def choose_time(callback: CallbackQuery, state: FSMContext) -> None:
    time = callback.data.split(":", 1)[1]
    data = await state.update_data(time=time)
    await state.set_state(BookingFlow.confirm)
    day = format_day(date.fromisoformat(data["day"]))
    await callback.message.edit_text(
        "Перевірте запис:\n\n"
        f"💈 {html.quote(data['service'])}\n"
        f"📅 {day}\n"
        f"🕙 {time}\n"
        f"💵 {data['price']} грн",
        reply_markup=kb.confirm_kb(),
    )
    await callback.answer()


@router.callback_query(BookingFlow.confirm, F.data == "confirm")
async def confirm(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot, config: Config) -> None:
    data = await state.get_data()
    user = callback.from_user
    booking_id = db.add_booking(user.id, user.full_name, data["service"], data["day"], data["time"])

    if booking_id is None:
        # Поки клієнт думав, цей час зайняв хтось інший: повертаємо до вибору часу
        day = date.fromisoformat(data["day"])
        slots = free_slots(day, db.taken_times(data["day"]), now_local(), WORK_START, WORK_END)
        if slots:
            await state.set_state(BookingFlow.time)
            await callback.message.edit_text(
                "На жаль, цей час щойно зайняли. Оберіть інший:", reply_markup=kb.times_kb(slots)
            )
        else:
            await state.set_state(BookingFlow.day)
            await callback.message.edit_text(
                "На жаль, на цей день вільного часу вже немає. Оберіть інший день:",
                reply_markup=kb.days_kb(days_for_booking()),
            )
        await callback.answer()
        return

    await state.clear()
    booking = db.get_booking(booking_id)
    await callback.message.edit_text(f"✅ Ви записані!\n\n{describe(booking)}\n\nЧекаємо на вас.")
    await callback.answer()
    await notify_admin(
        bot,
        config,
        f"🆕 Новий запис №{booking.id}\n\n{describe(booking)}\n"
        f"Клієнт: {html.link(html.quote(user.full_name), f'tg://user?id={user.id}')}",
    )


# --- Кнопки «Назад» і «Скасувати» --------------------------------------------


@router.callback_query(F.data == "back:services")
async def back_to_services(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BookingFlow.service)
    await callback.message.edit_text("Оберіть послугу:", reply_markup=kb.services_kb())
    await callback.answer()


@router.callback_query(F.data == "back:days")
async def back_to_days(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BookingFlow.day)
    await callback.message.edit_text("Оберіть день:", reply_markup=kb.days_kb(days_for_booking()))
    await callback.answer()


@router.callback_query(BookingFlow.confirm, F.data == "back:times")
async def back_to_times(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    day = date.fromisoformat(data["day"])
    slots = free_slots(day, db.taken_times(data["day"]), now_local(), WORK_START, WORK_END)
    await state.set_state(BookingFlow.time)
    await callback.message.edit_text(
        f"День: <b>{format_day(day)}</b>\n\nОберіть час:", reply_markup=kb.times_kb(slots)
    )
    await callback.answer()


@router.callback_query(F.data == "stop")
async def stop_booking(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Запис скасовано. Щоб почати знову, натисніть «✂️ Записатися».")
    await callback.answer()


# --- Мої записи --------------------------------------------------------------


@router.message(F.text == kb.BTN_MY)
async def my_bookings(message: Message, db: Database) -> None:
    bookings = db.user_bookings(message.from_user.id, now_local().date().isoformat())
    if not bookings:
        await message.answer("У вас немає активних записів.")
        return
    for booking in bookings:
        await message.answer(describe(booking), reply_markup=kb.cancel_booking_kb(booking))


@router.callback_query(F.data.startswith("cancel:"))
async def cancel_booking(callback: CallbackQuery, db: Database, bot: Bot, config: Config) -> None:
    booking = db.get_booking(int(callback.data.split(":")[1]))
    if booking is None or not db.cancel_booking(booking.id, callback.from_user.id):
        await callback.message.edit_text("Цей запис уже скасовано.")
        await callback.answer()
        return

    await callback.message.edit_text(f"❌ Запис скасовано\n\n{describe(booking)}")
    await callback.answer()
    await notify_admin(
        bot,
        config,
        f"❌ Клієнт скасував запис №{booking.id}\n\n{describe(booking)}\n"
        f"Клієнт: {html.quote(booking.user_name)}",
    )
