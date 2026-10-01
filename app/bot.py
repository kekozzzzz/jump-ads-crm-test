import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from app import db

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher(storage=MemoryStorage())


class LeadForm(StatesGroup):
    name = State()
    contact = State()
    request = State()


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.set_state(LeadForm.name)
    await message.answer(
        "Привет! Это бот агентства. Чтобы оставить заявку, ответьте на пару вопросов.\n"
        "Как вас зовут?"
    )


@dp.message(LeadForm.name)
async def name_handler(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(LeadForm.contact)
    await message.answer("Оставьте контакт для связи (телефон, email или телеграм):")


@dp.message(LeadForm.contact)
async def contact_handler(message: Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await state.set_state(LeadForm.request)
    await message.answer("Коротко опишите, что вас интересует:")


@dp.message(LeadForm.request)
async def request_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    lead_id = db.create_lead(
        name=data["name"],
        contact=data["contact"],
        request=message.text,
        source="telegram_bot",
    )
    await state.clear()
    await message.answer(
        f"Спасибо! Заявка #{lead_id} принята, скоро с вами свяжутся."
    )


@dp.message(F.text)
async def fallback_handler(message: Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        await message.answer("Напишите /start, чтобы оставить заявку.")
