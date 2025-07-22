import requests
import json
import time
import random
import sqlite3
from datetime import datetime

SERVER_URL = "https://python.topcam.ai.vn/api/student/list"
DB_FILE = "students_local.db"

def save_to_sqlite(students):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            vector_face TEXT
        )
    """)
    c.execute("DELETE FROM students")
    for s in students:
        c.execute(
            "INSERT INTO students (id, full_name, vector_face) VALUES (?, ?, ?)",
            (s["id"], s["full_name"], json.dumps(s["vector_face"]))
        )
    conn.commit()
    conn.close()
    print(f"Đã lưu {len(students)} học sinh vào database local {DB_FILE}")

def fetch_students():
    now = datetime.now()
    if not (now.hour == 1 or now.hour == 13):
        print("Không nằm trong khung giờ cập nhật, dừng lại.")
        return

    try:
        delay = random.randint(0, 1800)
        print(f"Đợi {delay} giây trước khi lấy danh sách...")
        time.sleep(delay)

        response = requests.get(SERVER_URL, timeout=10)
        data = response.json()
        if not data.get("success"):
            print("Không lấy được danh sách học sinh:", data.get("message"))
            return

        students = data.get("data", [])
        filtered_students = [
            {
                "id": s.get("id"),
                "full_name": s.get("full_name"),
                "vector_face": s.get("vector_face")
            }
            for s in students
            if s.get("id") and s.get("full_name")
        ]

        save_to_sqlite(filtered_students)

    except Exception as e:
        print("Lỗi khi lấy danh sách:", e)

if __name__ == "__main__":
    fetch_students()