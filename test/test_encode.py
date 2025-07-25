import requests
import base64
import json

def encode_image_to_base64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

url = 'https://python.topcam.ai.vn/api/face_vector_encode'

payload = {
    "image_front": encode_image_to_base64("test/front.jpg"),
    "image_left": encode_image_to_base64("test/left.jpg"),
    "image_right": encode_image_to_base64("test/right.jpg")
}
with open("payload_debug.json", "w", encoding="utf-8") as f:
    json.dump(payload, f)

print("Payload đã được ghi ra file payload_debug.json")
response = requests.post(url, json=payload)

if response.status_code == 200:
    print("Response JSON:", response.json())
else:
    print("Error:", response.status_code, response.text)
