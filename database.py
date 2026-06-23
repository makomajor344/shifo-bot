import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "shifo24.db")


# ================= DB CONNECTION =================
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ================= INIT DB =================
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Doctors table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            username TEXT,
            specialty TEXT NOT NULL,
            experience TEXT NOT NULL,
            district TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            balance REAL DEFAULT 0,
            rating REAL DEFAULT 5.0,
            rating_count INTEGER DEFAULT 0,
            busy INTEGER DEFAULT 0
        )
    ''')

    # Calls table (FIXED: finished_at qo'shildi)
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


# ================= DOCTOR =================
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


def get_doctor_by_id(doctor_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doctors WHERE doctor_id = ?", (doctor_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_doctors_by_filter(district, specialty):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM doctors
        WHERE district = ?
        AND specialty = ?
        AND status = 'approved'
        AND busy = 0
        AND balance >= 10000
    ''', (district, specialty))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def approve_doctor(doctor_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE doctors SET status='approved' WHERE doctor_id=?", (doctor_id,))
    conn.commit()
    conn.close()


def reject_doctor(doctor_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM doctors WHERE doctor_id=?", (doctor_id,))
    conn.commit()
    conn.close()


def add_balance(doctor_id, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE doctors SET balance = balance + ? WHERE doctor_id=?", (amount, doctor_id))
    conn.commit()
    conn.close()


def deduct_balance(doctor_id, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE doctors SET balance = balance - ? WHERE doctor_id=?", (amount, doctor_id))
    conn.commit()
    conn.close()


def set_busy(doctor_id, busy):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE doctors SET busy=? WHERE doctor_id=?", (busy, doctor_id))
    conn.commit()
    conn.close()


# ================= RATING =================
def add_rating(doctor_id, score):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT rating, rating_count FROM doctors WHERE doctor_id=?", (doctor_id,))
    row = cursor.fetchone()

    if row:
        rating = row["rating"]
        count = row["rating_count"]

        new_count = count + 1
        new_rating = round(((rating * count) + score) / new_count, 1)

        cursor.execute("""
            UPDATE doctors
            SET rating=?, rating_count=?
            WHERE doctor_id=?
        """, (new_rating, new_count, doctor_id))

        conn.commit()

    conn.close()


# ================= CALLS =================
def create_call(patient_id, doctor_id, patient_name, phone, age, address, complaint):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO calls (patient_id, doctor_id, patient_name, phone, age, address, complaint)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (patient_id, doctor_id, patient_name, phone, age, address, complaint))

    call_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return call_id


def get_call(call_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM calls WHERE id=?", (call_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_call(call_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE calls SET status=? WHERE id=?", (status, call_id))
    conn.commit()
    conn.close()


def update_call_finish_time(call_id, finish_time):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE calls SET finished_at=? WHERE id=?",
        (finish_time, call_id)
    )
    conn.commit()
    conn.close()