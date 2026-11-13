"""Старт, довідка, ціни, контакти і відповіді на все незрозуміле."""

from __future__ import annotations

from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import keyboards as kb
from config import CONTACTS, SALON_NAME, SERVICES, Config

router = Router()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        f"Вітаю, {html.quote(message.from_user.first_name)}! 👋\n\n"
        f"Це бот запису до <b>{SALON_NAME}</b>. Оберіть дію в меню нижче.",
        reply_markup=kb.main_menu(),
    )


@router.message(Command("help"))
async def help_command(message: Message, config: Config) -> None:
    text = (
        f"{kb.BTN_BOOK}: обрати послугу, день і час\n"
        f"{kb.BTN_MY}: переглянути або скасувати запис\n"
        f"{kb.BTN_PRICES}: список послуг\n"
        f"{kb.BTN_CONTACTS}: адреса і графік"
    )
    if config.admin_id and message.from_user.id == config.admin_id:
        text += "\n\nДля адміністратора:\n/today, /tomorrow, /day РРРР-ММ-ДД: розклад на день"
    await message.answer(text)


@router.message(Command("id"))
async def my_id(message: Message) -> None:
    """Показує Telegram ID: його треба вписати в ADMIN_ID у файлі .env."""
    await message.answer(f"Ваш Telegram ID: <code>{message.from_user.id}</code>")


@router.message(F.text == kb.BTN_PRICES)
async def prices(message: Message) -> None:
    lines = [f"• {html.quote(s.name)}: <b>{s.price} грн</b>, {s.minutes} хв" for s in SERVICES]
    await message.answer("💈 <b>Послуги та ціни</b>\n\n" + "\n".join(lines))


@router.message(F.text == kb.BTN_CONTACTS)
async def contacts(message: Message) -> None:
    await message.answer(f"<b>{SALON_NAME}</b>\n\n{CONTACTS}")


@router.message()
async def unknown_message(message: Message) -> None:
    await message.answer("Не зрозумів 🙂 Скористайтеся кнопками меню.", reply_markup=kb.main_menu())


@router.callback_query()
async def stale_button(callback: CallbackQuery) -> None:
    """Натиснули кнопку зі старого повідомлення, коли запис уже завершено або перервано."""
    await callback.answer("Ця кнопка вже неактивна. Натисніть «✂️ Записатися» ще раз.", show_alert=True)
