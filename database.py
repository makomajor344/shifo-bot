import sqlite3
import os
from datetime import datetime

# Bot qayerdan ishga tushishidan qat'iy nazar, bazani aynan bot turgan papkaga bog'lab qo'yadi.
# Bu cmd orqali kirganda ma'lumotlar yo'qolib qolishining oldini oladi.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "shifo24.db")

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Shifokorlar jadvali (IF NOT EXISTS - agar bor bo'lsa teginmaydi, o'chirib yubormaydi)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            username TEXT,
            specialty TEXT NOT NULL,
            experience TEXT NOT NULL,
            district TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            balance REAL DEFAULT 0.0,
            rating REAL DEFAULT 5.0,
            rating_count INTEGER DEFAULT 0,
            busy INTEGER DEFAULT 0
        )
    ''')
    
    # Chaqiruvlar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            patient_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            age TEXT NOT NULL,
            address TEXT NOT NULL,
            complaint TEXT NOT NULL,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
# YANI: Chaqiruv yaratilganda vaqtni saqlash
def create_call(patient_id, doctor_id, patient_name, phone, age, address, complaint):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO calls (patient_id, doctor_id, patient_name, phone, age, address, complaint, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')
    ''', (patient_id, doctor_id, patient_name, phone, age, address, complaint, now))
    call_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return call_id

# YANI: Chaqiruv yakunlanganda vaqtni saqlash
def update_call_finish_time(call_id, finish_time):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE calls SET finished_at = ? WHERE id = ?", (finish_time, call_id))
    conn.commit()
    conn.close()
def add_doctor(doctor_id, full_name, username, specialty, experience, district):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO doctors (doctor_id, full_name, username, specialty, experience, district, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
            ON CONFLICT(doctor_id) DO UPDATE SET
                full_name=excluded.full_name,
                username=excluded.username,
                specialty=excluded.specialty,
                experience=excluded.experience,
                district=excluded.district,
                status='pending'
        ''', (doctor_id, full_name, username, specialty, experience, district))
        conn.commit()
    finally:
        conn.close()

def get_doctors_by_filter(district, specialty):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM doctors 
        WHERE district = ? AND specialty = ? AND status = 'approved' AND busy = 0 AND balance >= 10000
    ''', (district, specialty))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_doctor_by_id(doctor_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM doctors WHERE doctor_id = ?', (doctor_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def approve_doctor(doctor_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE doctors SET status = 'approved' WHERE doctor_id = ?", (doctor_id,))
    conn.commit()
    conn.close()

def reject_doctor(doctor_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM doctors WHERE doctor_id = ?", (doctor_id,))
    conn.commit()
    conn.close()

def add_balance(doctor_id, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE doctors SET balance = balance + ? WHERE doctor_id = ?", (amount, doctor_id))
    conn.commit()
    conn.close()

def deduct_balance(doctor_id, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE doctors SET balance = balance - ? WHERE doctor_id = ?", (amount, doctor_id))
    conn.commit()
    conn.close()

def set_busy(doctor_id, busy_status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE doctors SET busy = ? WHERE doctor_id = ?", (busy_status, doctor_id))
    conn.commit()
    conn.close()

def add_rating(doctor_id, score):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT rating, rating_count FROM doctors WHERE doctor_id = ?', (doctor_id,))
        row = cursor.fetchone()
        
        if row:
            doc = dict(row)
            if doc['rating_count'] == 0:
                new_rating = float(score)
                new_count = 1
            else:
                new_count = doc['rating_count'] + 1
                new_rating = round(((doc['rating'] * doc['rating_count']) + score) / new_count, 1)
            
            cursor.execute('''
                UPDATE doctors 
                SET rating = ?, rating_count = ? 
                WHERE doctor_id = ?
            ''', (new_rating, new_count, doctor_id))
            conn.commit()
    finally:
        conn.close()

def create_call(patient_id, doctor_id, patient_name, phone, age, address, complaint):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO calls (patient_id, doctor_id, patient_name, phone, age, address, complaint)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (patient_id, doctor_id, patient_name, phone, age, address, complaint))
        call_id = cursor.lastrowid
        conn.commit()
        return call_id
    finally:
        conn.close()

def get_call(call_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM calls WHERE id = ?', (call_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_call(call_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE calls SET status = ? WHERE id = ?", (status, call_id))
    conn.commit()
    conn.close()