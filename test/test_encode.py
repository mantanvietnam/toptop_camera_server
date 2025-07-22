import requests
import base64

def encode_image_to_base64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

url = 'http://localhost:5002/api/encode'

payload = {
    "image_front": encode_image_to_base64("front.jpg"),
    "image_left": encode_image_to_base64("left.jpg"),
    "image_right": encode_image_to_base64("right.jpg")
}

response = requests.post(url, json=payload)

print("Status Code:", response.status_code)
print("Response JSON:", response.json())
