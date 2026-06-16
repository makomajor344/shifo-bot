import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

import database as db

# ================= SERVER QISMI (RENDER UCHUN) =================

async def health_check(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ================= KEEPALIVE QISMI =================

async def keep_alive():
    while True:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("https://shifo24.onrender.com") as resp:
                    logging.info(f"Keep-alive ping: {resp.status}")
        except Exception as e:
            logging.error(f"Keep-alive xatosi: {e}")
        await asyncio.sleep(300)

# ===============================================================

# Loggingni yoqish
logging.basicConfig(level=logging.INFO)

TOKEN = "8756099041:AAFpgLFHqx1bSQQEwpz9_ZM3lvSn7z99vM8"
ADMIN_ID = 1934997334

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# ================= STATES (FSM) =================
class DocRegister(StatesGroup):
    district = State()
    name = State()
    spec = State()
    exp = State()

class PatOrder(StatesGroup):
    district = State()
    spec = State()
    select_doc = State()
    name = State()
    phone = State()
    age = State()
    address = State()
    complaint = State()

class AdminStates(StatesGroup):
    wait_amount = State()

# ================= DATA =================
districts = [
    "Nukus shahri", "Nukus tumani", "Amudaryo", "Beruniy", "Chimboy",
    "Ellikqala", "Kegeyli", "Moynoq", "Qongirot", "Qoraozak",
    "Shumanay", "Taxtakopir", "Tortkol", "Xojayli"
]

specs = [
    "Terapevt", "Umumiy amaliyot", "Oilaviy shifokor",
    "Kardiolog", "Nevropatolog", "Psixiatr", "Endokrinolog",
    "Gastroenterolog", "Nefrolog", "Pulmonolog", "Ginekolog",
    "Pediatr", "Dermatolog", "Oftalmolog", "LOR", "Jarroh",
    "Ortoped", "Urolog", "Onkolog", "Stomatolog", "Reanimatolog"
]

def build_grid_keyboard(items, prefix):
    inline_keyboard = []
    row = []
    for i, item in enumerate(items):
        row.append(InlineKeyboardButton(text=item, callback_data=f"{prefix}_{i}"))
        if len(row) == 2:
            inline_keyboard.append(row)
            row = []
    if row:
        inline_keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

# SIZNING build_grid_keyboard FUNKSIYANGIZDAN KEYIN:

async def keep_alive():
    while True:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("https://shifo-bot.onrender.com") as resp:
                    logging.info(f"Keep-alive ping: {resp.status}")
        except Exception as e:
            logging.error(f"Keep-alive xatosi: {e}")
        await asyncio.sleep(300)

# KEYIN ESA SHU YERDAN HANDLERLARINGIZ (dp.message va b.) BOSHLANADI
# ================= START =================
@dp.message(CommandStart())
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍⚕️ Shifokor (Ro'yxatdan o'tish)", callback_data="role_doc")],
        [InlineKeyboardButton(text="🧑 Bemor (Chaqiruv qilish)", callback_data="role_pat")]
    ])
    await m.answer("🏥 <b>@SHIFO24_bot</b> ga xush kelibsiz! Tizimga kirish uchun rolingizni tanlang:", reply_markup=kb)

# ================= ROLE SELECTION =================
@dp.callback_query(F.data == "role_doc")
async def role_doc(c: types.CallbackQuery, state: FSMContext):
    uid = c.from_user.id
    existing_doc = db.get_doctor_by_id(uid)
    if existing_doc:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Profilni qayta faollashtirish", callback_data="doc_re_verify")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="role_doc_cancel")]
        ])
        status_txt = "Tasdiqlangan" if existing_doc['status'] == 'approved' else "Kutilmoqda / Rad etilgan"
        await c.message.answer(
            f"ℹ️ <b>Siz tizimda ro'yxatdan o'tgansiz!</b>\n\n"
            f"👤 Ism: {existing_doc['full_name']}\n"
            f"🩺 Mutaxassislik: {existing_doc['specialty']}\n"
            f"💰 Eski balans: {existing_doc['balance']} so'm\n"
            f"📊 Joriy holat: {status_txt}\n\n"
            f"Profilingizni qayta faollashtirish va adminga so'rov yuborish uchun tugmani bosing:",
            reply_markup=kb
        )
        await c.answer()
        return
    await state.set_state(DocRegister.district)
    kb = build_grid_keyboard(districts, "doc_d")
    await c.message.answer("📍 Shifokor sifatida hududingizni tanlang:", reply_markup=kb)
    await c.answer()

@dp.callback_query(F.data == "role_pat")
async def role_pat(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(PatOrder.district)
    kb = build_grid_keyboard(districts, "pat_d")
    await c.message.answer("📍 Bemor sifatida yashash hududingizni tanlang:", reply_markup=kb)
    await c.answer()

# ================= DOCTOR REGISTER FLOW =================
@dp.callback_query(DocRegister.district, F.data.startswith("doc_d_"))
async def doc_district(c: types.CallbackQuery, state: FSMContext):
    i = int(c.data.split("_")[2])
    await state.update_data(district=districts[i])
    await state.set_state(DocRegister.name)
    await c.message.answer("📝 Ism va Familiyangizni kiriting:\n<i>(Masalan: Aybek Teshaboev)</i>")
    await c.answer()

@dp.message(DocRegister.name)
async def doc_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await state.set_state(DocRegister.spec)
    kb = build_grid_keyboard(specs, "doc_s")
    await m.answer("🩺 Mutaxassisligingizni tanlang:", reply_markup=kb)

@dp.callback_query(DocRegister.spec, F.data.startswith("doc_s_"))
async def doc_spec(c: types.CallbackQuery, state: FSMContext):
    i = int(c.data.split("_")[2])
    await state.update_data(spec=specs[i])
    await state.set_state(DocRegister.exp)
    await c.message.answer("⏳ Ish stajingizni kiriting <i>(Masalan: 5 yil)</i>:")
    await c.answer()

@dp.message(DocRegister.exp)
async def doc_exp(m: types.Message, state: FSMContext):
    data = await state.get_data()
    uid = m.from_user.id
    username = m.from_user.username or "yo'q"
    try:
        db.add_doctor(uid, data['name'], username, data['spec'], m.text, data['district'])
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Tasdiqlash", callback_data=f"admin_app_{uid}")],
            [InlineKeyboardButton(text="🔴 Rad etish", callback_data=f"admin_rej_{uid}")],
        ])
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🆕 <b>SHIFOKOR ARIZASI:</b>\n\n"
                f"🆔 ID: {uid}\n"
                f"👤 F.I.O: {data['name']}\n"
                f"🩺 Mutaxassislik: {data['spec']}\n"
                f"⏳ Staj: {m.text}\n"
                f"📍 Hudud: {data['district']}\n"
                f"🔗 Username: @{username}",
                reply_markup=admin_kb
            )
            await m.answer(f"✅ Ma'lumotlaringiz qabul qilindi. Arizangiz admin ko'rib chiqishi uchun yuborildi.\n\n⚠️ Tasdiqlanish uchun iltimos admin bilan bog'laning: @admishifo24")
        except Exception as admin_err:
            logging.error(f"Adminga xabar yuborishda xato: {admin_err}")
            await m.answer(f"✅ Arizangiz bazaga muvaffaqiyatli saqlandi. Ammo adminga bildirishnoma bormadi.")
    except Exception as db_err:
        logging.error(f"Baza (database) xatoligi: {db_err}")
        await m.answer(f"❌ Xatolik yuz berdi! Ma'lumotlarni bazaga saqlab bo'lmadi.\n\n<code>{str(db_err)}</code>")
    await state.clear()

# ================= RE-VERIFY FOR OLD DOCTORS =================
@dp.callback_query(F.data == "doc_re_verify")
async def doc_re_verify(c: types.CallbackQuery):
    uid = c.from_user.id
    doc = db.get_doctor_by_id(uid)
    username = c.from_user.username or "yo'q"
    if not doc:
        await c.message.answer("❌ Xatolik: Ma'lumotlaringiz topilmadi.")
        await c.answer()
        return
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Qayta faollashtirish", callback_data=f"admin_app_{uid}")],
        [InlineKeyboardButton(text="🔴 Rad etish", callback_data=f"admin_rej_{uid}")],
    ])
    await bot.send_message(
        ADMIN_ID,
        f"⚠️ <b>ESKI SHIFOKOR PROFILINI QAYTA FAOLLASHTIRMOQCHI!</b>\n\n"
        f"🆔 ID: {uid}\n"
        f"👤 F.I.O: {doc['full_name']}\n"
        f"🩺 Mutaxassislik: {doc['specialty']}\n"
        f"📍 Hudud: {doc['district']}\n"
        f"💰 <b>Eski balansi: {doc['balance']} so'm</b>\n"
        f"⭐ Reytingi: {doc['rating']}\n"
        f"🔗 Username: @{username}\n\n"
        f"Ushbu shifokor tizimda bor. Uni qayta tasdiqlaysizmi?",
        reply_markup=admin_kb
    )
    await c.message.answer("✅ Arizangiz adminga yuborildi. Admin tasdiqlashi bilan profilingiz qayta ishga tushadi.")
    await c.answer()

@dp.callback_query(F.data == "role_doc_cancel")
async def role_doc_cancel(c: types.CallbackQuery):
    await c.message.answer("Amal bekor qilindi. Bosh menyuga qaytish uchun /start bosing.")
    await c.answer()

# ================= PATIENT ORDER FLOW =================
@dp.callback_query(PatOrder.district, F.data.startswith("pat_d_"))
async def pat_district(c: types.CallbackQuery, state: FSMContext):
    i = int(c.data.split("_")[2])
    await state.update_data(district=districts[i])
    await state.set_state(PatOrder.spec)
    kb = build_grid_keyboard(specs, "pat_s")
    await c.message.answer("🩺 Qaysi soha shifokori kerak? Tanlang:", reply_markup=kb)
    await c.answer()

@dp.callback_query(PatOrder.spec, F.data.startswith("pat_s_"))
async def pat_spec(c: types.CallbackQuery, state: FSMContext):
    i = int(c.data.split("_")[2])
    spec = specs[i]
    data = await state.get_data()
    dist = data['district']
    await state.update_data(spec=spec)
    doctors = db.get_doctors_by_filter(dist, spec)
    if not doctors:
        retry_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Boshqa mutaxassislik tanlash", callback_data="change_spec_retry")],
            [InlineKeyboardButton(text="📍 Hududni o'zgartirish", callback_data="role_pat")]
        ])
        await c.message.answer(
            f"❌ Kechirasiz, siz tanlagan <b>{dist}</b> hududida hozircha bo'sh <b>{spec}</b> topilmadi.\n\n"
            f"Quyidagi tugmalardan birini tanlab, qidiruvni davom ettirishingiz mumkin:", 
            reply_markup=retry_kb
        )
        await c.answer()
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👨‍⚕️ {d['full_name']} (Staj: {d['experience']}, ⭐{d['rating']})", callback_data=f"choose_doc_{d['doctor_id']}")]
        for d in doctors
    ])
    await state.set_state(PatOrder.select_doc)
    await c.message.answer("👇 Quyidagi shifokorlardan birini tanlang:", reply_markup=kb)
    await c.answer()

@dp.callback_query(F.data == "change_spec_retry")
async def change_spec_retry(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(PatOrder.spec)
    kb = build_grid_keyboard(specs, "pat_s")
    await c.message.answer("🩺 Qaysi soha shifokori kerak? Tanlang:", reply_markup=kb)
    await c.answer()

@dp.callback_query(PatOrder.select_doc, F.data.startswith("choose_doc_"))
async def pat_select_doc(c: types.CallbackQuery, state: FSMContext):
    did = int(c.data.split("_")[2])
    doctor = db.get_doctor_by_id(did)
    if not doctor or doctor['balance'] < 10000:
        await c.message.answer("❌ Tanlangan shifokor xizmat ko'rsata olmaydi (Balans kamligi sababli). Boshqa shifokor tanlang.")
        return
    await state.update_data(doctor_id=did)
    await state.set_state(PatOrder.name)
    await c.message.answer("📝 Ism va Familiyangizni kiriting:")
    await c.answer()

@dp.message(PatOrder.name)
async def pat_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await state.set_state(PatOrder.phone)
    await m.answer("📞 Telefon raqamingizni kiriting:\n<i>(Masalan: +998901234567)</i>")

@dp.message(PatOrder.phone)
async def pat_phone(m: types.Message, state: FSMContext):
    if not any(char.isdigit() for char in m.text):
        await m.answer("⚠️ Iltimos, haqiqiy telefon raqamini kiriting:")
        return
    await state.update_data(phone=m.text)
    await state.set_state(PatOrder.age)
    await m.answer("🔢 Yoshingizni kiriting:")

@dp.message(PatOrder.age)
async def pat_age(m: types.Message, state: FSMContext):
    if not m.text.isdigit():
        await m.answer("⚠️ Iltimos yoshingizni faqat raqamlarda kiriting (Masalan: 25):")
        return
    await state.update_data(age=m.text)
    await state.set_state(PatOrder.address)
    await m.answer("🏠 To'liq manzilingizni kiriting (Ko'cha, uy):")
@dp.message(PatOrder.address)
async def pat_address(m: types.Message, state: FSMContext):
    try:
        # Manzilni saqlash
        await state.update_data(address=m.text)
        
        # Keyingi holatga o'tish
        await state.set_state(PatOrder.complaint)
        
        # Bemorga javob yuborish
        await m.answer("📝 Endi shifokorga murojaat qilish sababingizni (ariza mazmunini) qisqacha yozing:")
        
        # Log yozish (agar qotib qolsa, logda ko'rinadi)
        logging.info(f"User {m.from_user.id} address set. Next: complaint.")
    except Exception as e:
        # Xatolik bo'lsa logga yozish
        logging.error(f"Error in pat_address: {e}")
        await m.answer("❌ Xatolik yuz berdi. Iltimos, /start buyrug'ini yuborib qaytadan urinib ko'ring.")
        await state.clear()
@dp.message(PatOrder.complaint)
async def pat_complaint(m: types.Message, state: FSMContext):
    data = await state.get_data()
    pid = m.from_user.id
    did = data['doctor_id']
    doctor_info = db.get_doctor_by_id(did)
    doc_name_txt = doctor_info['full_name'] if doctor_info else "Noma'lum"
    cid = db.create_call(pid, did, data['name'], data['phone'], data['age'], data['address'], m.text)
    doc_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Qabul qilish", callback_data=f"doc_accept_{cid}"),
            InlineKeyboardButton(text="🔴 Rad etish", callback_data=f"doc_reject_{cid}")
        ]
    ])
    await bot.send_message(
        did,
        f"🔔 <b>YANGI ARIZA KELDI!</b>\n\n"
        f"👤 Bemor: {data['name']}\n"
        f"🔢 Yoshi: {data['age']}\n"
        f"📍 Hudud: {data['district']}\n"
        f"📝 Murojaat sababi: {m.text}\n\n"
        f"Arizani qabul qilasizmi?",
        reply_markup=doc_kb
    )
    try:
        await bot.send_message(
            ADMIN_ID,
            f"📢 <b>YANGI ARIZA QOLDIRILDI (ID: {cid}):</b>\n\n"
            f"🧑 <b>Bemor:</b> {data['name']} ({data['phone']})\n"
            f"🏠 <b>Manzil:</b> {data['address']}\n"
            f"📝 <b>Murojaat sababi:</b> {m.text}\n\n"
            f"👨‍⚕️ <b>Tanlangan Shifokor:</b> {doc_name_txt} (ID: <code>{did}</code>)\n"
            f"📊 <b>Holati:</b> Yangi ariza, shifokor javobi kutilmoqda..."
        )
    except Exception as e:
        logging.error(f"Adminga ariza xabarini yuborishda xato: {e}")
    await m.answer("✅ Arizangiz shifokorga yuborildi. Shifokor tasdig'ini kuting...")
    await state.clear()

# ================= DOCTOR RESPONSE HANDLERS =================
@dp.callback_query(F.data.startswith("doc_accept_"))
async def doc_accept(c: types.CallbackQuery):
    cid = int(c.data.split("_")[2])
    call = db.get_call(cid)
    if not call or call['status'] != 'new':
        await c.message.answer("Bu chaqiruv eskirgan yoki bekor qilingan.")
        await c.answer()
        return
    db.update_call(cid, 'accepted_by_doc')
    pat_agree_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🤝 Roziman", callback_data=f"pat_agree_{cid}"),
            InlineKeyboardButton(text="❌ Rad etaman", callback_data=f"pat_cancel_{cid}")
        ]
    ])
    await bot.send_message(
        call['patient_id'],
        f"🟢 Shifokor sizning chaqiruvingizni qabul qildi!\n\n"
        f"⚠️ <b>DIQQAT:</b>\n"
        f"💵 Konsulturaliya narxi: 30 000 so'm.\n"
        f"Taxi qo'shimcha ravishda bemor tomonidan to'lanadi.\n\n"
        f"Shartlarga rozimisiz?",
        reply_markup=pat_agree_kb
    )
    await c.message.answer("✅ Bemorga rozilik so'rovi yuborildi.")
    await c.answer()

@dp.callback_query(F.data.startswith("doc_reject_"))
async def doc_reject(c: types.CallbackQuery):
    cid = int(c.data.split("_")[2])
    call = db.get_call(cid)
    if call:
        db.update_call(cid, 'rejected_by_doc')
        await bot.send_message(call['patient_id'], "🔴 Afsuski, shifokor hozirda bandligi sababli chaqiruvingizni rad etdi.")
        try:
            await bot.send_message(ADMIN_ID, f"❌ <b>ID {cid} li ariza rad etildi.</b> Shifokor arizani rad etdi.")
        except: pass
    await c.message.answer("🔴 Chaqiruv rad etildi.")
    await c.answer()

# ================= PATIENT AGREEMENT HANDLERS =================
@dp.callback_query(F.data.startswith("pat_agree_"))
async def pat_agree(c: types.CallbackQuery):
    cid = int(c.data.split("_")[2])
    call = db.get_call(cid)
    if not call or call['status'] != 'accepted_by_doc':
        await c.message.answer("Bu buyurtma jarayoni yakunlangan.")
        await c.answer()
        return
    db.update_call(cid, 'in_progress')
    db.set_busy(call['doctor_id'], 1)
    finish_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏁 Konsultatsiyani yakunlash", callback_data=f"finish_call_{cid}")]
    ])
    await bot.send_message(
        call['doctor_id'],
        f"🚀 <b>Bemor shartlarga rozi bo'ldi!</b>\n\n"
        f"📝 <b>BEMOR MA'LUMOTLARI:</b>\n"
        f"👤 Ismi: {call['patient_name']}\n"
        f"📞 Telefon: {call['phone']}\n"
        f"🔢 Yoshi: {call['age']}\n"
        f"🏠 Manzil: {call['address']}\n"
        f"🤒 Murojaat: {call['complaint']}\n\n"
        f"⚠️ Jarayonni tugatgach, quyidagi tugmani bosing!",
        reply_markup=finish_kb
    )
    try:
        await bot.send_message(
            ADMIN_ID,
            f"🚕 <b>CHAQIRUV BOSHLANDI (ID: {cid}):</b>\n"
            f"👨‍⚕️ Shifokor ID: {call['doctor_id']}\n"
            f"🧑 Bemor ID: {call['patient_id']}\n"
            f"📍 Manzil: {call['address']}"
        )
    except:
        pass
    await c.message.answer("✅ Rahmat! Roziligingiz shifokorga yuborildi. Tez orada yetib boradi.")
    await c.answer()

@dp.callback_query(F.data.startswith("pat_cancel_"))
async def pat_cancel(c: types.CallbackQuery):
    cid = int(c.data.split("_")[2])
    call = db.get_call(cid)
    if call:
        db.update_call(cid, 'cancelled_by_patient')
        await bot.send_message(call['doctor_id'], "🔴 Bemor shartlarga rozi bo'lmadi, chaqiruv bekor qilindi.")
        try:
            await bot.send_message(ADMIN_ID, f"🧑❌ <b>ID {cid} li ariza bekor qilindi.</b> Bemor shartlarga rozi bo'lmadi.")
        except: pass
    await c.message.answer("❌ Chaqiruv bekor qilindi.")
    await c.answer()

# ================= FINISH AND RATING =================
@dp.callback_query(F.data.startswith("finish_call_"))
async def finish_call(c: types.CallbackQuery):
    cid = int(c.data.split("_")[2])
    call = db.get_call(cid)
    if not call or call['status'] != 'in_progress':
        await c.message.answer("Bu chaqiruv allaqachon yakunlangan.")
        await c.answer()
        return
    did = call['doctor_id']
    db.update_call(cid, 'done')
    db.set_busy(did, 0)
    db.deduct_balance(did, 10000)
    rate_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{i} ⭐", callback_data=f"rate_{did}_{i}") for i in range(1, 6)]
    ])
    await bot.send_message(call['patient_id'], "🏥 Konsultatsiya yakunlandi. Shifo tilaymiz! Shifokor xizmatini baholang:", reply_markup=rate_kb)
    await c.message.answer("💰 Chaqiruv yakunlandi. Balansingizdan 10 000 so'm yechildi.")
    try:
        await bot.send_message(ADMIN_ID, f"🏁 <b>ID {cid} li ariza muvaffaqiyatli yakunlandi!</b>")
    except: pass
    await c.answer()

@dp.callback_query(F.data.startswith("rate_"))
async def rate_doc_callback(c: types.CallbackQuery):
    _, did, score = c.data.split("_")
    did = int(did)
    score = int(score)
    db.add_rating(did, score)
    await c.message.answer("❤️ Baholaganingiz uchun rahmat!")
    await c.answer()

# ================= BALANCE & ADMIN PANEL =================
@dp.message(Command("balance"))
async def check_balance(m: types.Message):
    doc = db.get_doctor_by_id(m.from_user.id)
    if doc:
        await m.answer(f"💰 Sizning balansingiz: {doc['balance']} so'm\nStatus: {doc['status'].upper()}\nBandlik: {'Band 🛑' if doc['busy']==1 else 'Bo\'sh 🟢'}")
    else:
        await m.answer("❌ Siz shifokorlar ro'yxatida yo'qsiz.")

@dp.message(Command("admin"))
async def admin_panel(m: types.Message):
    if m.from_user.id != ADMIN_ID: return
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍⚕️ Barcha Shifokorlar", callback_data="admin_list_docs")],
        [InlineKeyboardButton(text="📋 Barcha Chaqiriqlar", callback_data="admin_list_calls")]
    ])
    await m.answer(
        "🏥 <b>ADMIN PANELGA XUSH KELIBSIZ!</b>\n\n"
        "Buyruqlar:\n"
        "<code>/fill_balance [shifokor_id]</code> - Shifokor balansini to'ldirish\n\n"
        "Quyidagi tugmalar orqali bazani ko'rishingiz mumkin:", 
        reply_markup=admin_kb
    )

@dp.message(Command("fill_balance"))
async def fill_balance_start(m: types.Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID: return
    try:
        args = m.text.split()
        target_id = int(args[1])
        await state.update_data(target_doc_id=target_id)
        await state.set_state(AdminStates.wait_amount)
        await m.answer(f"💵 ID: <code>{target_id}</code> bo'lgan shifokorga qancha mablag' (so'm) qo'shmoqchisiz? Faqat raqam yozing:")
    except:
        await m.answer("⚠️ To'g'ri formatda yozing. Masalan: <code>/fill_balance 1934997334</code>")

@dp.message(AdminStates.wait_amount)
async def fill_balance_save(m: types.Message, state: FSMContext):
    if m.from_user.id != ADMIN_ID: return
    try:
        amount = int(m.text)
        data = await state.get_data()
        did = data['target_doc_id']
        db.add_balance(did, amount)
        await m.answer(f"✅ ID: {did} shifokor balansiga {amount} so'm qo'shildi.")
        await bot.send_message(did, f"💰 Admin balansingizni {amount} so'mga to'ldirdi!")
        await state.clear()
    except ValueError:
        await m.answer("❌ Iltimos faqat raqam kiriting:")

# ================= ADMIN ACTIONS & LIST SHOW =================
@dp.callback_query(F.data.startswith("admin_app_"))
async def admin_approve(c: types.CallbackQuery):
    if c.from_user.id != ADMIN_ID: return
    did = int(c.data.split("_")[2])
    db.approve_doctor(did)
    await bot.send_message(did, "🟢 Arizangiz admin tomonidan tasdiqlandi! Balansingizni to'ldirib, buyurtmalarni qabul qilishingiz mumkin.")
    await c.message.answer("🟢 Shifokor tasdiqlandi.")
    await c.answer()

@dp.callback_query(F.data.startswith("admin_rej_"))
async def admin_reject(c: types.CallbackQuery):
    if c.from_user.id != ADMIN_ID: return
    did = int(c.data.split("_")[2])
    db.reject_doctor(did)
    await bot.send_message(did, "🔴 Arizangiz admin tomonidan rad etildi.")
    await c.message.answer("🔴 Shifokor arizasi rad etildi va o'chirildi.")
    await c.answer()

@dp.callback_query(F.data == "admin_list_docs")
async def admin_list_docs(c: types.CallbackQuery):
    if c.from_user.id != ADMIN_ID: return
    conn = db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doctors")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        await c.message.answer("📭 Bazada birorta ham shifokor yo'q.")
        await c.answer()
        return
    text = "👨‍⚕️ <b>BAZADAGI SHIFOKORLAR RO'YXATI:</b>\n\n"
    for r in rows:
        status_emoji = "🟢" if r['status'] == 'approved' else "🟡"
        busy_emoji = "🛑 Band" if r['busy'] == 1 else "🟢 Bo'sh"
        text += (
            f"{status_emoji} <b>{r['full_name']}</b>\n"
            f"🆔 ID: <code>{r['doctor_id']}</code>\n"
            f"🩺 Soha: {r['specialty']} | ⏳ Staj: {r['experience']}\n"
            f"📍 Hudud: {r['district']}\n"
            f"💰 Balans: {r['balance']} so'm\n"
            f"🔄 Holat: {busy_emoji}\n"
            f"---------------------------\n"
        )
    if len(text) > 4096:
        for x in range(0, len(text), 4096):
            await c.message.answer(text[x:x+4096])
    else:
        await c.message.answer(text)
    await c.answer()

@dp.callback_query(F.data == "admin_list_calls")
async def admin_list_calls(c: types.CallbackQuery):
    if c.from_user.id != ADMIN_ID: return
    conn = db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM calls ORDER BY id DESC LIMIT 20")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        await c.message.answer("📭 Tizimda hali chaqiriqlar bo'lmagan.")
        await c.answer()
        return
    text = "📋 <b>OXIRGI CHAQIRIQLAR RO'YXATI (MAX 20 TA):</b>\n\n"
    for r in rows:
        status_map = {
            'new': "🆕 Yangi",
            'accepted_by_doc': "👨‍⚕️ Shifokor qabul qildi",
            'rejected_by_doc': "❌ Shifokor rad etdi",
            'in_progress': "🚀 Jarayonda (Shifokor yo'lda)",
            'cancelled_by_patient': "🧑 Bemor bekor qildi",
            'done': "🏁 Yakunlandi"
        }
        status_txt = status_map.get(r['status'], r['status'])
        text += (
            f"🔢 <b>Chaqiruv ID: {r['id']}</b>\n"
            f"🧑 Bemor: {r['patient_name']} ({r['phone']})\n"
            f"🏠 Manzil: {r['address']}\n"
            f"👨‍⚕️ Shifokor ID: <code>{r['doctor_id']}</code>\n"
            f"🤒 Murojaat: {r['complaint']}\n"
            f"📊 Status: <b>{status_txt}</b>\n"
            f"---------------------------\n"
        )
    if len(text) > 4096:
        for x in range(0, len(text), 4096):
            await c.message.answer(text[x:x+4096])
    else:
        await c.message.answer(text)
    await c.answer()

# ================= POLLING =================
async def main():
    db.init_db()
    asyncio.create_task(start_web_server())
    asyncio.create_task(keep_alive())

    logging.info("Bot ishga tushirilmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Polling boshlandi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())