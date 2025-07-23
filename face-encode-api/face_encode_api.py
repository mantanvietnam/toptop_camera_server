import base64
import cv2
import numpy as np
from flask import Flask, request, jsonify
import logging
import insightface
from insightface.app import FaceAnalysis
from insightface.utils import face_align

# Cấu hình log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Khởi tạo Flask app
app = Flask(__name__)

# Khởi tạo model InsightFace
try:
    face_app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider'])
    face_app.prepare(ctx_id=0)
    logger.info("✅ Đã khởi tạo InsightFace với GPU (CUDAExecutionProvider).")
except Exception as e:
    logger.warning(f"⚠️ Không dùng được GPU: {e}. Chuyển sang CPU.")
    face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
    face_app.prepare(ctx_id=0)
    logger.info("✅ Đã khởi tạo InsightFace với CPU (CPUExecutionProvider).")

def base64_to_image(base64_string):
    """Chuyển base64 string thành ảnh OpenCV"""
    try:
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        img_data = base64.b64decode(base64_string)
        np_arr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        logger.error(f"❌ Lỗi giải mã base64: {e}")
        return None

@app.route('/api/encode', methods=['POST'])
def encode_face_from_images():
    """API nhận 3 ảnh base64 và trả về vector trung bình nếu hợp lệ"""
    try:
        data = request.get_json()
        if not data:
            logger.warning("📭 Không có dữ liệu gửi lên.")
            return jsonify({'success': False, 'message': 'Không có dữ liệu gửi lên', 'error_code': 400}), 400

        images_base64 = [
            data.get('image_front'),
            data.get('image_left'),
            data.get('image_right'),
        ]

        directions = ['front', 'left', 'right']
        vectors = []
        for idx, base64_str in enumerate(images_base64):
            direction = directions[idx]
            logger.info(f"📥 Xử lý ảnh hướng: {direction.upper()}")

            if not base64_str:
                logger.warning(f"❌ Ảnh {direction} không hợp lệ (trống).")
                return jsonify({'success': False, 'message': f'Ảnh thứ {idx+1} không hợp lệ, vui lòng tải lại.', 'error_code': 401}), 400

            img = base64_to_image(base64_str)
            if img is None:
                logger.warning(f"❌ Không đọc được ảnh {direction}.")
                return jsonify({'success': False, 'message': f'Không đọc được ảnh thứ {idx+1}, vui lòng tải lại.', 'error_code': 402}), 400

            logger.info(f"📏 Kích thước ảnh {direction}: {img.shape}")

            faces = face_app.get(img)
            if not faces or faces[0].det_score < 0.7:
                score = faces[0].det_score if faces else 0
                logger.warning(f"❌ Không phát hiện khuôn mặt rõ ở ảnh {direction} (score: {score:.3f})")
                return jsonify({'success': False, 'message': f'Không phát hiện khuôn mặt rõ ràng ở ảnh thứ {idx+1}, vui lòng tải lại.', 'error_code': 403}), 400

            face = faces[0]

            logger.info(f"✅ Ảnh {direction.upper()} hợp lệ, đang lấy embedding...")
            vectors.append(face.embedding)

        # Tính vector trung bình
        avg_vector = np.mean(vectors, axis=0)
        logger.info("✅ Đã tính xong vector trung bình.")

        return jsonify({
            'success': True,
            'vector': avg_vector.tolist()
        }), 200

    except Exception as e:
        logger.exception(f"🔥 Lỗi encode face: {e}")
        return jsonify({'success': False, 'message': f'Lỗi server: {str(e)}', 'error_code': 500}), 500

if __name__ == '__main__':
    logger.info("🚀 Face Encode API đang chạy tại http://0.0.0.0:5002")
    app.run(host='0.0.0.0', port=5002, debug=False)
