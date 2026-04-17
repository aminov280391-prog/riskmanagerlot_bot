import os
import asyncio
import logging
import random
import string
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ========== КОНФИГУРАЦИЯ ==========
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN not set")
ADMIN_ID = 543784246   # замените на свой ID

# ========== ПЕРЕВОДЫ ==========
LANGUAGES = {
    "en": "🇬🇧 English",
    "ru": "🇷🇺 Русский",
    "uz": "🇺🇿 O‘zbek",
    "zh": "🇨🇳 中文",
    "tr": "🇹🇷 Türkçe"
}

LOC = {
    "btn_calc": {"en": "🎯 Calculate Lot", "ru": "🎯 Рассчитать лот", "uz": "🎯 Lotni hisoblash", "zh": "🎯 计算手数", "tr": "🎯 Lot Hesapla"},
    "btn_reset": {"en": "🔄 Reset", "ru": "🔄 Сброс", "uz": "🔄 Bekor qilish", "zh": "🔄 重置", "tr": "🔄 Sıfırla"},
    "btn_contact": {"en": "📞 Contact Admin", "ru": "📞 Связаться с админом", "uz": "📞 Admin bilan bog‘lanish", "zh": "📞 联系管理员", "tr": "📞 Admin ile iletişim"},
    "btn_instruments": {"en": "📋 Instruments", "ru": "📋 Инструменты", "uz": "📋 Vositalar", "zh": "📋 交易品种", "tr": "📋 Enstrümanlar"},
    "btn_language": {"en": "🌐 Language", "ru": "🌐 Язык", "uz": "🌐 Til", "zh": "🌐 语言", "tr": "🌐 Dil"},
    "btn_history": {"en": "📜 History", "ru": "📜 История", "uz": "📜 Tarix", "zh": "📜 历史记录", "tr": "📜 Geçmiş"},
    "welcome": {
        "en": "📊 *Lot Calculator*\n\nPress '{}' to begin.\nReset: '{}'\nContact admin: '{}'\nHistory: '{}'",
        "ru": "📊 *Калькулятор лота*\n\nНажмите «{}» для начала.\nСброс: «{}»\nСвязаться с админом: «{}»\nИстория: «{}»",
        "uz": "📊 *Lot kalkulyatori*\n\nBoshlash: '{}'\nBekor qilish: '{}'\nAdmin: '{}'\nTarix: '{}'",
        "zh": "📊 *手数计算器*\n\n按“{}”开始。\n重置：“{}”\n联系管理员：“{}”\n历史记录：“{}”",
        "tr": "📊 *Lot Hesaplayıcı*\n\nBaşlamak: '{}'\nSıfırlama: '{}'\nAdmin: '{}'\nGeçmiş: '{}'"
    },
    "instruments_list": {
        "en": "📋 *Available instruments:*\n```\n{}\n```",
        "ru": "📋 *Доступные инструменты:*\n```\n{}\n```",
        "uz": "📋 *Mavjud vositalar:*\n```\n{}\n```",
        "zh": "📋 *可用品种:*\n```\n{}\n```",
        "tr": "📋 *Mevcut enstrümanlar:*\n```\n{}\n```"
    },
    "select_instrument": {"en": "🔽 *Select instrument:*", "ru": "🔽 *Выберите инструмент:*", "uz": "🔽 *Vositani tanlang:*", "zh": "🔽 *选择品种:*", "tr": "🔽 *Enstrüman seçin:*"},
    "invalid_instrument": {"en": "❌ Please select from buttons.", "ru": "❌ Выберите из кнопок.", "uz": "❌ Tugmalardan tanlang.", "zh": "❌ 请从按钮中选择。", "tr": "❌ Butonlardan seçin."},
    "instrument_selected": {
        "en": "✅ Instrument: {}\n💰 *Enter deposit (USD):*",
        "ru": "✅ Инструмент: {}\n💰 *Введите депозит (USD):*",
        "uz": "✅ Vosita: {}\n💰 *Depozitni kiriting (USD):*",
        "zh": "✅ 品种: {}\n💰 *输入入金（美元）:*",
        "tr": "✅ Enstrüman: {}\n💰 *Depozito girin (USD):*"
    },
    "enter_open": {"en": "📈 *Enter open price* (e.g., 1950.50):", "ru": "📈 *Введите цену открытия*", "uz": "📈 *Ochilish narxi*", "zh": "📈 *输入开仓价*", "tr": "📈 *Açılış fiyatı*"},
    "enter_sl": {"en": "📉 *Enter stop loss price*:", "ru": "📉 *Введите стоп-лосс*:", "uz": "📉 *Stop loss narxi*:", "zh": "📉 *输入止损价*:", "tr": "📉 *Stop loss fiyatı*:"},
    "risk_type_prompt": {"en": "⚖️ *Select risk type:*", "ru": "⚖️ *Тип риска:*", "uz": "⚖️ *Risk turi:*", "zh": "⚖️ *风险类型:*", "tr": "⚖️ *Risk tipi:*"},
    "risk_percent": {"en": "Percent of deposit", "ru": "Процент от депозита", "uz": "Depozitdan foiz", "zh": "入金百分比", "tr": "Depozito yüzdesi"},
    "risk_fixed": {"en": "Fixed amount (USD)", "ru": "Фиксированная сумма", "uz": "Belgilangan miqdor", "zh": "固定金额", "tr": "Sabit tutar"},
    "enter_risk_percent": {"en": "📊 *Enter risk in %* (e.g., 2):", "ru": "📊 *Риск в %* (например, 2):", "uz": "📊 *Risk foizi* (masalan, 2):", "zh": "📊 *风险百分比*（例如 2）:", "tr": "📊 *Risk yüzdesi* (örnek: 2):"},
    "enter_risk_fixed": {"en": "💰 *Enter fixed risk amount (USD):*", "ru": "💰 *Фиксированная сумма риска (USD):*", "uz": "💰 *Belgilangan risk miqdori (USD):*", "zh": "💰 *固定风险金额（美元）:*", "tr": "💰 *Sabit risk tutarı (USD):*"},
    "error_positive": {"en": "❌ Enter a positive number.", "ru": "❌ Введите положительное число.", "uz": "❌ Musbat son kiriting.", "zh": "❌ 请输入正数。", "tr": "❌ Pozitif sayı girin."},
    "result": {
        "en": "✅ *Recommended lot:* `{lot:.2f}`\n\n💰 *Deposit:* {deposit} USD\n📈 *Entry:* {open_price}\n🛑 *Stop Loss:* {sl_price}\n💸 *Risk:* {risk_text}\n📏 *Stop distance:* {points} pips",
        "ru": "✅ *Рекомендуемый лот:* `{lot:.2f}`\n\n💰 *Депозит:* {deposit} USD\n📈 *Точка входа:* {open_price}\n🛑 *Стоп-лосс:* {sl_price}\n💸 *Риск:* {risk_text}\n📏 *Расстояние до стопа:* {points} пунктов",
        "uz": "✅ *Tavsiya etilgan lot:* `{lot:.2f}`\n\n💰 *Depozit:* {deposit} USD\n📈 *Kirish narxi:* {open_price}\n🛑 *Stop Loss:* {sl_price}\n💸 *Risk:* {risk_text}\n📏 *Stop masofasi:* {points} punkt",
        "zh": "✅ *推荐手数:* `{lot:.2f}`\n\n💰 *入金:* {deposit} USD\n📈 *入场价:* {open_price}\n🛑 *止损价:* {sl_price}\n💸 *风险:* {risk_text}\n📏 *止损距离:* {points} 点",
        "tr": "✅ *Önerilen lot:* `{lot:.2f}`\n\n💰 *Depozito:* {deposit} USD\n📈 *Giriş fiyatı:* {open_price}\n🛑 *Stop Loss:* {sl_price}\n💸 *Risk:* {risk_text}\n📏 *Stop mesafesi:* {points} pip"
    },
    "cancel": {
        "en": "❌ Cancelled. Press '{}' to start again.",
        "ru": "❌ Отменено. Нажмите «{}».",
        "uz": "❌ Bekor qilindi. '{}' bosing.",
        "zh": "❌ 已取消。按“{}”重新开始。",
        "tr": "❌ İptal edildi. Yeniden başlamak için '{}'."
    },
    "reset_button_text": {"en": "🔄 Reset", "ru": "🔄 Сброс", "uz": "🔄 Bekor qilish", "zh": "🔄 重置", "tr": "🔄 Sıfırla"},
    "contact_request": {
        "en": "✍️ Please type your message to admin (text only, your ID will not be shown):",
        "ru": "✍️ Напишите ваше сообщение администратору (только текст, ваш ID не будет показан):",
        "uz": "✍️ Admonga xabaringizni yozing (faqat matn, ID-ingiz ko‘rsatilmaydi):",
        "zh": "✍️ 请输入您给管理员的消息（仅文本，您的ID不会显示）:",
        "tr": "✍️ Yöneticiye mesajınızı yazın (sadece metin, ID'niz gösterilmeyecek):"
    },
    "contact_admin_ok": {"en": "✅ Your message has been sent to admin.", "ru": "✅ Ваше сообщение отправлено администратору.", "uz": "✅ Xabaringiz adminga yuborildi.", "zh": "✅ 您的消息已发送给管理员。", "tr": "✅ Mesajınız yöneticiye gönderildi."},
    "contact_invalid": {
        "en": "❌ Please send a text message.",
        "ru": "❌ Пожалуйста, отправьте текстовое сообщение.",
        "uz": "❌ Iltimos, matnli xabar yuboring.",
        "zh": "❌ 请发送文本消息。",
        "tr": "❌ Lütfen metin mesajı gönderin."
    },
    "contact_no_admin": {"en": "📧 Admin contact not set.", "ru": "📧 Контакт администратора не задан.", "uz": "📧 Admin kontakti o‘rnatilmagan.", "zh": "📧 管理员联系方式未设置。", "tr": "📧 Yönetici iletişimi ayarlanmamış."},
    "language_selected": {"en": "✅ Language changed.", "ru": "✅ Язык изменён.", "uz": "✅ Til o‘zgartirildi.", "zh": "✅ 语言已更改。", "tr": "✅ Dil değiştirildi."},
    "choose_language": {"en": "🌐 *Choose language:*", "ru": "🌐 *Выберите язык:*", "uz": "🌐 *Tilni tanlang:*", "zh": "🌐 *选择语言:*", "tr": "🌐 *Dil seçin:*"},
    "history_empty": {
        "en": "📜 No calculations yet. Press '{}' to start.",
        "ru": "📜 Расчётов пока нет. Нажмите «{}».",
        "uz": "📜 Hali hech qanday hisob yo‘q. '{}' bosing.",
        "zh": "📜 暂无计算记录。按“{}”开始。",
        "tr": "📜 Henüz hesaplama yok. Başlamak için '{}'."
    },
    "history_title": {
        "en": "📜 *Your last calculations:*\n\n",
        "ru": "📜 *Ваши последние расчёты:*\n\n",
        "uz": "📜 *Sizning oxirgi hisoblaringiz:*\n\n",
        "zh": "📜 *您最近的计算记录:*\n\n",
        "tr": "📜 *Son hesaplamalarınız:*\n\n"
    },
    "history_entry": {
        "en": "🕒 {time}\nInstrument: {instr}\nDeposit: {deposit} USD\nLot: {lot:.2f}\nRisk: {risk_text}",
        "ru": "🕒 {time}\nИнструмент: {instr}\nДепозит: {deposit} USD\nЛот: {lot:.2f}\nРиск: {risk_text}",
        "uz": "🕒 {time}\nVosita: {instr}\nDepozit: {deposit} USD\nLot: {lot:.2f}\nRisk: {risk_text}",
        "zh": "🕒 {time}\n品种: {instr}\n入金: {deposit} USD\n手数: {lot:.2f}\n风险: {risk_text}",
        "tr": "🕒 {time}\nEnstrüman: {instr}\nDepozito: {deposit} USD\nLot: {lot:.2f}\nRisk: {risk_text}"
    },
    "error_general": {
        "en": "⚠️ Error: {error}\nStart over with /calc",
        "ru": "⚠️ Ошибка: {error}\nНачните заново /calc",
        "uz": "⚠️ Xato: {error}\n/calc bilan qaytadan",
        "zh": "⚠️ 错误: {error}\n使用 /calc 重新开始",
        "tr": "⚠️ Hata: {error}\n/calc ile yeniden başlayın"
    },
    "admin_reply_instruction": {
        "en": "To reply, use: `/reply {} your message`",
        "ru": "Чтобы ответить, используйте: `/reply {} ваше сообщение`",
        "uz": "Javob berish uchun: `/reply {} sizning xabaringiz`",
        "zh": "要回复，请使用：`/reply {} 您的消息`",
        "tr": "Yanıtlamak için şunu kullanın: `/reply {} mesajınız`"
    },
    "reply_sent_to_user": {
        "en": "✅ Reply sent to user.",
        "ru": "✅ Ответ отправлен пользователю.",
        "uz": "✅ Javob foydalanuvchiga yuborildi.",
        "zh": "✅ 回复已发送给用户。",
        "tr": "✅ Yanıt kullanıcıya gönderildi."
    },
    "reply_invalid_code": {
        "en": "❌ Invalid code. Active codes: {}",
        "ru": "❌ Неверный код. Активные коды: {}",
        "uz": "❌ Noto‘g‘ri kod. Faol kodlar: {}",
        "zh": "❌ 无效代码。活动代码：{}",
        "tr": "❌ Geçersiz kod. Aktif kodlar: {}"
    },
    "reply_error": {
        "en": "❌ Failed to send: {}",
        "ru": "❌ Ошибка отправки: {}",
        "uz": "❌ Yuborishda xato: {}",
        "zh": "❌ 发送失败：{}",
        "tr": "❌ Gönderme hatası: {}"
    }
}

# ========== ИНСТРУМЕНТЫ ==========
INSTRUMENTS = [
    "XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD", "USOIL", "UKOIL",
    "BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD", "ADAUSD", "DOTUSD",
    "NAS100", "SPX500", "US30", "DE40", "UK100", "JP225",
    "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCHF", "USDCAD",
    "AUDJPY", "CADJPY", "CHFJPY", "EURAUD", "EURGBP", "EURJPY", "GBPAUD", "GBPJPY", "GBPCAD", "NZDCAD"
]

INSTRUMENT_SPECS = {
    "XAUUSD": {"pip_size": 0.01, "point_value_usd": 1.0},
    "XAGUSD": {"pip_size": 0.01, "point_value_usd": 1.0},
    "XPTUSD": {"pip_size": 0.01, "point_value_usd": 1.0},
    "XPDUSD": {"pip_size": 0.01, "point_value_usd": 1.0},
    "USOIL": {"pip_size": 0.01, "point_value_usd": 1.0},
    "UKOIL": {"pip_size": 0.01, "point_value_usd": 1.0},
    "BTCUSD": {"pip_size": 1.0, "point_value_usd": 1.0},
    "ETHUSD": {"pip_size": 1.0, "point_value_usd": 1.0},
    "LTCUSD": {"pip_size": 1.0, "point_value_usd": 1.0},
    "XRPUSD": {"pip_size": 1.0, "point_value_usd": 1.0},
    "ADAUSD": {"pip_size": 1.0, "point_value_usd": 1.0},
    "DOTUSD": {"pip_size": 1.0, "point_value_usd": 1.0},
    "NAS100": {"pip_size": 1.0, "point_value_usd": 1.0},
    "SPX500": {"pip_size": 1.0, "point_value_usd": 1.0},
    "US30": {"pip_size": 1.0, "point_value_usd": 1.0},
    "DE40": {"pip_size": 1.0, "point_value_usd": 1.0},
    "UK100": {"pip_size": 1.0, "point_value_usd": 1.0},
    "JP225": {"pip_size": 1.0, "point_value_usd": 1.0},
    "EURUSD": {"pip_size": 0.0001, "point_value_usd": 10.0},
    "GBPUSD": {"pip_size": 0.0001, "point_value_usd": 10.0},
    "AUDUSD": {"pip_size": 0.0001, "point_value_usd": 10.0},
    "NZDUSD": {"pip_size": 0.0001, "point_value_usd": 10.0},
    "USDCHF": {"pip_size": 0.0001, "point_value_usd": 10.0},
    "USDCAD": {"pip_size": 0.0001, "point_value_usd": 10.0},
    "USDJPY": {"pip_size": 0.01, "point_value_usd": 10.0},
    "AUDJPY": {"pip_size": 0.01, "point_value_usd": 10.0},
    "CADJPY": {"pip_size": 0.01, "point_value_usd": 10.0},
    "CHFJPY": {"pip_size": 0.01, "point_value_usd": 10.0},
    "EURJPY": {"pip_size": 0.01, "point_value_usd": 10.0},
    "GBPJPY": {"pip_size": 0.01, "point_value_usd": 10.0},
    "EURAUD": {"pip_size": 0.0001, "point_value_usd": 10.0},
    "EURGBP": {"pip_size": 0.0001, "point_value_usd": 10.0},
    "GBPAUD": {"pip_size": 0.0001, "point_value_usd": 10.0},
    "GBPCAD": {"pip_size": 0.0001, "point_value_usd": 10.0},
    "NZDCAD": {"pip_size": 0.0001, "point_value_usd": 10.0},
}

def calculate_lot(instrument, deposit, open_price, sl_price, risk_type, risk_value):
    specs = INSTRUMENT_SPECS.get(instrument)
    if not specs:
        return {"error": "Instrument not found"}
    if deposit <= 0 or open_price <= 0 or sl_price <= 0:
        return {"error": "Deposit and prices must be positive"}
    if risk_value <= 0:
        return {"error": "Risk must be > 0"}
    if risk_type == "percent":
        risk_usd = deposit * (risk_value / 100)
        risk_text = f"{risk_value}% = {risk_usd:.2f} USD"
    else:
        risk_usd = risk_value
        risk_text = f"{risk_value:.2f} USD"
    points = abs(open_price - sl_price) / specs["pip_size"]
    if points <= 0:
        return {"error": "Stop loss equals open price"}
    lot = risk_usd / (points * specs["point_value_usd"])
    lot = max(0.01, round(lot // 0.01) * 0.01)
    return {"lot": lot, "points": round(points, 1), "risk_text": risk_text}

# ========== ХРАНЕНИЕ ДАННЫХ ==========
user_langs = {}
user_history = {}
user_last_params = {}
reply_codes = {}

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

def add_to_history(user_id, entry):
    if user_id not in user_history:
        user_history[user_id] = []
    user_history[user_id].insert(0, entry)
    if len(user_history[user_id]) > 10:
        user_history[user_id].pop()

# ========== FSM ==========
class CalcForm(StatesGroup):
    waiting_for_instrument = State()
    waiting_for_deposit = State()
    waiting_for_open = State()
    waiting_for_sl = State()
    waiting_for_risk_type = State()
    waiting_for_risk_value = State()

class ContactForm(StatesGroup):
    waiting_for_message = State()

# ========== ИНИЦИАЛИЗАЦИЯ ==========
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

def get_lang(user_id):
    return user_langs.get(user_id, "en")

def get_text(user_id, key, *args, **kwargs):
    lang = get_lang(user_id)
    text = LOC.get(key, {}).get(lang, LOC.get(key, {}).get("en", key))
    if args or kwargs:
        return text.format(*args, **kwargs)
    return text

def main_keyboard(user_id):
    lang = get_lang(user_id)
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text=LOC["btn_calc"][lang])],
            [types.KeyboardButton(text=LOC["btn_reset"][lang]), types.KeyboardButton(text=LOC["btn_history"][lang])],
            [types.KeyboardButton(text=LOC["btn_instruments"][lang]), types.KeyboardButton(text=LOC["btn_contact"][lang])],
            [types.KeyboardButton(text=LOC["btn_language"][lang])]
        ], resize_keyboard=True
    )

def instrument_keyboard():
    kb = [[types.KeyboardButton(text=i) for i in INSTRUMENTS[j:j+3]] for j in range(0, len(INSTRUMENTS), 3)]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)

def risk_type_keyboard(user_id):
    lang = get_lang(user_id)
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text=LOC["risk_percent"][lang])],
            [types.KeyboardButton(text=LOC["risk_fixed"][lang])]
        ], resize_keyboard=True
    )

# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    u = message.from_user.id
    btn_calc = get_text(u, "btn_calc")
    btn_reset = get_text(u, "btn_reset")
    btn_contact = get_text(u, "btn_contact")
    btn_history = get_text(u, "btn_history")
    await message.answer(
        get_text(u, "welcome", btn_calc, btn_reset, btn_contact, btn_history),
        parse_mode="Markdown", reply_markup=main_keyboard(u)
    )

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    u = message.from_user.id
    await state.clear()
    btn_calc = get_text(u, "btn_calc")
    await message.answer(get_text(u, "cancel", btn_calc), reply_markup=main_keyboard(u))

@dp.message(Command("instruments"))
async def cmd_instruments(message: types.Message):
    u = message.from_user.id
    await message.answer(
        get_text(u, "instruments_list", "\n".join(INSTRUMENTS)),
        parse_mode="Markdown", reply_markup=main_keyboard(u)
    )

@dp.message(Command("language"))
async def cmd_language(message: types.Message):
    u = message.from_user.id
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=name)] for name in LANGUAGES.values()],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer(get_text(u, "choose_language"), parse_mode="Markdown", reply_markup=kb)

@dp.message(lambda msg: msg.text in LANGUAGES.values())
async def set_language(message: types.Message):
    u = message.from_user.id
    for code, name in LANGUAGES.items():
        if name == message.text:
            user_langs[u] = code
            await message.answer(get_text(u, "language_selected"), reply_markup=main_keyboard(u))
            return

@dp.message(Command("calc"))
async def cmd_calc(message: types.Message, state: FSMContext):
    u = message.from_user.id
    await state.clear()   # принудительный сброс перед новым расчётом
    await state.set_state(CalcForm.waiting_for_instrument)
    await message.answer(
        get_text(u, "select_instrument"),
        parse_mode="Markdown", reply_markup=instrument_keyboard()
    )

@dp.message(F.text.in_([LOC["btn_calc"][lang] for lang in LANGUAGES]))
async def handle_calc_button(message: types.Message, state: FSMContext):
    await cmd_calc(message, state)

@dp.message(F.text.in_([LOC["btn_reset"][lang] for lang in LANGUAGES]))
async def handle_reset_button(message: types.Message, state: FSMContext):
    await cmd_cancel(message, state)

@dp.message(F.text.in_([LOC["btn_history"][lang] for lang in LANGUAGES]))
async def show_history(message: types.Message):
    u = message.from_user.id
    history = user_history.get(u, [])
    if not history:
        btn_calc = get_text(u, "btn_calc")
        await message.answer(get_text(u, "history_empty", btn_calc), reply_markup=main_keyboard(u))
        return
    text = get_text(u, "history_title")
    for rec in history[:5]:
        text += get_text(u, "history_entry",
                         time=rec["time"], instr=rec["instrument"],
                         deposit=rec["deposit"], lot=rec["lot"],
                         risk_text=rec["risk_text"]) + "\n\n"
    await message.answer(text, parse_mode="Markdown", reply_markup=main_keyboard(u))

@dp.message(F.text.in_([LOC["btn_instruments"][lang] for lang in LANGUAGES]))
async def handle_instruments_button(message: types.Message):
    await cmd_instruments(message)

@dp.message(F.text.in_([LOC["btn_language"][lang] for lang in LANGUAGES]))
async def handle_language_button(message: types.Message):
    await cmd_language(message)

# ========== КНОПКА СВЯЗИ С АДМИНОМ ==========
@dp.message(F.text.in_([LOC["btn_contact"][lang] for lang in LANGUAGES]))
async def contact_admin_start(message: types.Message, state: FSMContext):
    u = message.from_user.id
    await state.set_state(ContactForm.waiting_for_message)
    await message.answer(get_text(u, "contact_request"), reply_markup=types.ReplyKeyboardRemove())

@dp.message(ContactForm.waiting_for_message)
async def contact_admin_send(message: types.Message, state: FSMContext):
    u = message.from_user.id
    if not message.text or not message.text.strip():
        await message.answer(get_text(u, "contact_invalid"), reply_markup=main_keyboard(u))
        await state.clear()
        return
    user_text = message.text.strip()
    if ADMIN_ID:
        code = generate_code()
        reply_codes[code] = u
        admin_msg = (
            f"📩 *New anonymous message*\n"
            f"🔑 *Code:* `{code}`\n\n"
            f"{user_text}\n\n"
            f"To reply, use: `/reply {code} your message`"
        )
        try:
            await bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
            await message.answer(get_text(u, "contact_admin_ok"), reply_markup=main_keyboard(u))
        except Exception as e:
            # Если бот не может отправить админу (админ не начал диалог)
            await message.answer(
                "❌ Could not reach admin. Make sure the admin has started the bot first.\n"
                "❌ Администратор ещё не запустил бота. Напишите ему напрямую.",
                reply_markup=main_keyboard(u)
            )
    else:
        await message.answer(get_text(u, "contact_no_admin"), reply_markup=main_keyboard(u))
    await state.clear()

# ========== КОМАНДЫ АДМИНА ==========
@dp.message(Command("list_codes"))
async def list_codes(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    if not reply_codes:
        await message.answer("No active codes.")
    else:
        codes_list = "\n".join([f"`{code}` -> user_id: {uid}" for code, uid in reply_codes.items()])
        await message.answer(f"Active codes:\n{codes_list}", parse_mode="Markdown")

@dp.message(Command("reply"))
async def admin_reply(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /reply CODE your message")
        return
    code = parts[1].strip().upper()
    reply_text = parts[2].strip()
    if not reply_text:
        await message.answer("Message cannot be empty.")
        return
    user_id = reply_codes.get(code)
    if not user_id:
        active = ", ".join(reply_codes.keys())
        await message.answer(get_text(ADMIN_ID, "reply_invalid_code", active))
        return
    try:
        await bot.send_message(user_id, f"📩 *Admin reply:*\n\n{reply_text}", parse_mode="Markdown")
        await message.answer(get_text(ADMIN_ID, "reply_sent_to_user"))
        del reply_codes[code]
    except Exception as e:
        await message.answer(get_text(ADMIN_ID, "reply_error", str(e)))

# ========== FSM ШАГИ ==========
@dp.message(CalcForm.waiting_for_instrument)
async def process_instrument(message: types.Message, state: FSMContext):
    u = message.from_user.id
    selected = message.text
    if selected not in INSTRUMENT_SPECS:
        await message.answer(get_text(u, "invalid_instrument"))
        return
    await state.update_data(instrument=selected)
    await state.set_state(CalcForm.waiting_for_deposit)
    await message.answer(
        get_text(u, "instrument_selected", selected),
        parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(CalcForm.waiting_for_deposit)
async def process_deposit(message: types.Message, state: FSMContext):
    u = message.from_user.id
    try:
        dep = float(message.text.replace(",", "."))
        if dep <= 0: raise ValueError
        await state.update_data(deposit=dep)
        await state.set_state(CalcForm.waiting_for_open)
        await message.answer(get_text(u, "enter_open"), parse_mode="Markdown")
    except:
        await message.answer(get_text(u, "error_positive"))

@dp.message(CalcForm.waiting_for_open)
async def process_open(message: types.Message, state: FSMContext):
    u = message.from_user.id
    try:
        op = float(message.text.replace(",", "."))
        if op <= 0: raise ValueError
        await state.update_data(open_price=op)
        await state.set_state(CalcForm.waiting_for_sl)
        await message.answer(get_text(u, "enter_sl"), parse_mode="Markdown")
    except:
        await message.answer(get_text(u, "error_positive"))

@dp.message(CalcForm.waiting_for_sl)
async def process_sl(message: types.Message, state: FSMContext):
    u = message.from_user.id
    try:
        sl = float(message.text.replace(",", "."))
        if sl <= 0: raise ValueError
        await state.update_data(sl_price=sl)
        await state.set_state(CalcForm.waiting_for_risk_type)
        await message.answer(get_text(u, "risk_type_prompt"), parse_mode="Markdown", reply_markup=risk_type_keyboard(u))
    except:
        await message.answer(get_text(u, "error_positive"))

@dp.message(CalcForm.waiting_for_risk_type)
async def process_risk_type(message: types.Message, state: FSMContext):
    u = message.from_user.id
    text = message.text
    lang = get_lang(u)
    if text == LOC["risk_percent"][lang]:
        risk_type = "percent"
        prompt = get_text(u, "enter_risk_percent")
    elif text == LOC["risk_fixed"][lang]:
        risk_type = "fixed"
        prompt = get_text(u, "enter_risk_fixed")
    else:
        await message.answer(get_text(u, "invalid_instrument"))
        return
    await state.update_data(risk_type=risk_type)
    await state.set_state(CalcForm.waiting_for_risk_value)
    await message.answer(prompt, parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

@dp.message(CalcForm.waiting_for_risk_value)
async def process_risk_value(message: types.Message, state: FSMContext):
    u = message.from_user.id
    try:
        risk_val = float(message.text.replace(",", "."))
        if risk_val <= 0: raise ValueError
        data = await state.get_data()
        result = calculate_lot(
            data["instrument"], data["deposit"], data["open_price"],
            data["sl_price"], data["risk_type"], risk_val
        )
        if "error" in result:
            await message.answer(get_text(u, "error_general", error=result["error"]), reply_markup=main_keyboard(u))
        else:
            user_last_params[u] = {
                "instrument": data["instrument"],
                "deposit": data["deposit"],
                "open_price": data["open_price"],
                "sl_price": data["sl_price"],
                "risk_type": data["risk_type"],
                "risk_value": risk_val
            }
            await message.answer(
                get_text(u, "result",
                         lot=result["lot"],
                         deposit=data["deposit"],
                         open_price=data["open_price"],
                         sl_price=data["sl_price"],
                         risk_text=result["risk_text"],
                         points=result["points"]),
                parse_mode="Markdown", reply_markup=main_keyboard(u)
            )
            add_to_history(u, {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "instrument": data["instrument"],
                "deposit": data["deposit"],
                "lot": result["lot"],
                "risk_text": result["risk_text"]
            })
        await state.clear()
    except Exception as e:
        await message.answer(get_text(u, "error_positive"), reply_markup=main_keyboard(u))
        await state.clear()

# ========== HEALTH CHECK ==========
async def health_check():
    from aiohttp import web
    app = web.Application()
    async def handle(request):
        return web.Response(text="OK")
    app.router.add_get('/', handle)
    app.router.add_get('/health', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()
    while True:
        await asyncio.sleep(3600)

async def set_bot_commands():
    commands = [
        types.BotCommand(command="start", description="🏠 Main menu"),
        types.BotCommand(command="calc", description="🧮 Calculate lot"),
        types.BotCommand(command="cancel", description="❌ Cancel current operation"),
        types.BotCommand(command="language", description="🌐 Change language"),
        types.BotCommand(command="instruments", description="📋 List of instruments"),
    ]
    await bot.set_my_commands(commands)

async def main():
    await set_bot_commands()
    await asyncio.gather(
        dp.start_polling(bot),
        health_check()
    )

if __name__ == "__main__":
    asyncio.run(main())
