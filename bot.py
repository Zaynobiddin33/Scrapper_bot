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
from tokens import *


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

router = Router()

dp.include_router(router)


# ---------- STATES ----------
class AddURL(StatesGroup):
    url = State()
    times = State()


# ---------- KEYBOARD ----------
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Link Qo'shish")],
        [KeyboardButton(text="▶️ Start")],
        [KeyboardButton(text="👁️ Linklarni ko'rish")],
        [KeyboardButton(text="🗑️ Linklarni tozalash")]
    ],
    resize_keyboard=True
)


# ---------- UTILS ----------



def clear_data():
    with open(DATA_FILE, "w") as f:
        json.dump([], f)


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


@dp.message(AddURL.url)
async def get_url(msg: types.Message, state: FSMContext):
    await state.update_data(url=msg.text)
    await msg.answer("Bu link'ga necha marta kirilsin?")
    await state.set_state(AddURL.times)


@dp.message(AddURL.times)
async def get_times(msg: types.Message, state: FSMContext):
    if not msg.text.isdigit():
        await msg.answer("Send a number.")
        return

    data = await state.get_data()
    save_data(data["url"], int(msg.text))

    await msg.answer(f"Saqlandi ✅\nSizda {count_links()}ta link mavjud", reply_markup=keyboard)
    await state.clear()


@dp.message(lambda m: m.text == "▶️ Start")
async def run_handler(msg: types.Message):
    mssg = await msg.answer("Boshlanmoqda...")

    data_list = load_data()

    for i, data in enumerate(data_list, start=1):
        if i == 1:
                    await mssg.edit_text(
                        f"{i}/{len(data_list)} linkga {data['times']} marta kirilmoqda...\n{show_stats(i-1, len(data_list))}"
                    )
        await asyncio.to_thread(
            run_fnc,
            data["url"],
            data["times"]
        )
        await mssg.edit_text(
            f"{i}/{len(data_list)} linkga {data['times']} marta kirilmoqda...\n{show_stats(i, len(data_list))}"
        )

        # 🔑 RUN SELENIUM IN THREAD

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