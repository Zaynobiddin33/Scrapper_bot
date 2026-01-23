import json
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from scrapper import run_fnc
from aiogram import types, Router
from pathlib import Path
from tokens import *

import json

data = {"interval": 100}

try:
    with open("interval.json", "x", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
except FileExistsError:
    pass  # file exists → do nothing


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

router = Router()

dp.include_router(router)


# ---------- STATES ----------
class AddURL(StatesGroup):
    url = State()
    times = State()


class GiveInterval(StatesGroup):
    interval = State()


# ---------- KEYBOARD ----------
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Link Qo'shish")],
        [KeyboardButton(text="▶️ Start")],
        [KeyboardButton(text="👁️ Linklarni ko'rish"),
         KeyboardButton(text="⏰ Vaqt intervalni o'zgartirish")],
        [KeyboardButton(text="🗑️ Linklarni tozalash")]
    ],
    resize_keyboard=True
)


# ---------- UTILS ----------



def clear_data():
    with open(DATA_FILE, "w") as f:
        json.dump([], f)

def update_interval(x):
    with open('interval.json', 'w') as f:
        json.dump({'interval':x}, f, indent=4)

def get_interval_number():
    with open('interval.json', 'r') as f:
        data = json.load(f)
        return data['interval']


def load_data():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except:
        return []


def textify_data():
    data = load_data()
    text = ''
    if data:
        for ind, i in enumerate(data, start=1):
            text+=f"{ind}) {i['url']} –– {i['times']}\n\n"
        return text
    else:
        return 'Sizda linklar mavjud emas'
    
def save_data(url, times):
    data = load_data()
    with open(DATA_FILE, "w") as f:
        data.append({"url": url, "times": times})
        json.dump(data, f)

def count_links():
    data = load_data()
    return len(data)


# ---------- YOUR FUNCTION ----------
def show_stats(done, all):
    if not done == 0:
        percentage = round(done/all*100)
        black = percentage//10
        white = 10-black
        return f'{"⬛"*black}{"⬜"*white} {percentage}%'
    else:
        return f"{'⬜'*10} 0%"


# ---------- HANDLERS ----------
@dp.message(CommandStart())
async def start(msg: types.Message):
    await msg.answer("Salom, Vazifa tanlang:", reply_markup=keyboard)


@dp.message(lambda m: m.text == "➕ Link Qo'shish")
async def add_url(msg: types.Message, state: FSMContext):
    await msg.answer("Link yuboring:")
    await state.set_state(AddURL.url)

@dp.message(lambda m: m.text == "👁️ Linklarni ko'rish")
async def add_url(msg: types.Message, state: FSMContext):
    await msg.answer(textify_data())


@dp.message(lambda m: m.text == "⏰ Vaqt intervalni o'zgartirish")
async def add_url(msg: types.Message, state: FSMContext):
    await msg.answer("Click vaqti oralig'ini yozing (sekundlarda):")
    await state.set_state(GiveInterval.interval)

@dp.message(GiveInterval.interval)
async def get_interval(msg: types.Message, state: FSMContext):
    try:
        number = int(msg.text)
        await state.update_data(interval = msg.text)
        update_interval(number)
        await msg.answer(f"Clicklar oralig'i {number} soniyaga o'zgartirildi ✅")
    except:
        await msg.answer("Iltimos faqat raqam kirgizing!:")
        await state.set_state(GiveInterval.interval)
        return



@dp.message(AddURL.url)
async def get_url(msg: types.Message, state: FSMContext):
    await state.update_data(url=msg.text)
    await msg.answer("Bu link'ga necha marta kirilsin?")
    await state.set_state(AddURL.times)


@dp.message(AddURL.times)
async def get_times(msg: types.Message, state: FSMContext):
    if not msg.text.isdigit():
        await msg.answer("Iltimos butun son jo'nating.")
        return

    data = await state.get_data()
    save_data(data["url"], int(msg.text))

    await msg.answer(f"Saqlandi ✅\nSizda {count_links()}ta link mavjud", reply_markup=keyboard)
    await state.clear()


@dp.message(lambda m: m.text == "▶️ Start")
async def run_handler(msg: types.Message):
    data_list = load_data()
    loop = asyncio.get_running_loop()

    for idx, data in enumerate(data_list, start=1):
        # 🆕 new message for THIS data
        progress_msg = await msg.answer(
            f"{idx}/{len(data_list)} linkga {data['times']} marta kirilmoqda...\n\n0/{data['times']}\n\n{show_stats(0, data['times'])}"
        )

        async def update(iteration, total):
            await progress_msg.edit_text(
                f"{idx}/{len(data_list)} linkga {data['times']} marta kirilmoqda...\n\n"
                f"{iteration}/{total}\n\n"
                f"{show_stats(iteration, total)}"
            )

        def progress_callback(iteration, total):
            asyncio.run_coroutine_threadsafe(
                update(iteration, total),
                loop
            )

        await asyncio.to_thread(
            run_fnc,
            data["url"],
            data["times"],
            get_interval_number(),
            progress_callback
        )

    clear_data()
    await msg.answer("Vazifa bajarildi ✅")

@dp.message(lambda m: m.text == "🗑️ Linklarni tozalash")
async def clear_urls_handler(msg: types.Message):
    yes_no_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o'chirilsin", callback_data="yes"),
            InlineKeyboardButton(text="❌ Yo'q, bekor qilish", callback_data="no")
        ]
    ])
    await msg.answer("Linklarni tozalashga ishonchingiz komilmi?", reply_markup=yes_no_kb)

@router.callback_query(lambda c: c.data in ["yes", "no"])
async def process_callback(callback: types.CallbackQuery):
    if callback.data == "yes":
        clear_data()
        await callback.message.edit_text("Linklar tozalandi")
    else:
        await callback.message.edit_text("Tozalash bekor qilindi")
    await callback.answer()  # to remove the "loading" state on the button

# ---------- START ----------
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())