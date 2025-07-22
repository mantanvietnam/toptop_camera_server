import requests
import json
import time
import random
from datetime import datetime

SERVER_URL = "https://python.topcam.ai.vn/api/student/list"

def fetch_students():
    # Chỉ chạy trong khung giờ 1h–2h hoặc 13h–14h
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

        with open("students_local.json", "w", encoding="utf-8") as f:
            json.dump(filtered_students, f, ensure_ascii=False, indent=2)
        print(f"Đã lưu {len(filtered_students)} học sinh vào students_local.json")
    except Exception as e:
        print("Lỗi khi lấy danh sách:", e)

if __name__ == "__main__":
    fetch_students()