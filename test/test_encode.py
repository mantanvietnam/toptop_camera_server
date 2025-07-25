import requests
import base64
import cv2
import numpy as np

def encode_image_to_base64(path, resize_shape=(640, 480)):
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Không tìm thấy file: {path}")
    # Resize ảnh
    img = cv2.resize(img, resize_shape)
    # Encode lại thành JPEG
    _, buffer = cv2.imencode('.jpg', img)
    img_bytes = buffer.tobytes()
    return base64.b64encode(img_bytes).decode('utf-8')

url = 'https://python.topcam.ai.vn/api/face_vector_encode'

payload = {
    "image_front": encode_image_to_base64("test/front.jpg"),
    "image_left": encode_image_to_base64("test/left.jpg"),
    "image_right": encode_image_to_base64("test/right.jpg")
}

response = requests.post(url, json=payload)

print("Status Code:", response.status_code)
try:
    print("Response JSON:", response.json())
except Exception:
    print("Response Text:", response.text)