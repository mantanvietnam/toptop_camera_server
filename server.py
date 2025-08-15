import mysql.connector
from flask import Flask, request, jsonify
import json
import base64
import numpy as np
from datetime import datetime
import logging
import cv2
import insightface
from insightface.app import FaceAnalysis
from insightface.utils import face_align
# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64 MB
# Cấu hình database - CẬP NHẬT
DB_CONFIG = {
    'host': '172.16.33.4',
    'port': 3306,
    'user': 'tranmanh_cameraai',
    'password': 'nWoNuPubC',
    'database': 'tranmanh_cameraai',
    'charset': 'utf8mb4'
}

class DatabaseManager:
    def __init__(self):
        self.config = DB_CONFIG
    
    def get_connection(self):
        try:
            connection = mysql.connector.connect(**self.config)
            logger.info("Database connection successful")
            return connection
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    def execute_query(self, query, params=None, fetch=True):
        connection = self.get_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params)
            
            if fetch:
                result = cursor.fetchall()
            else:
                connection.commit()
                result = cursor.rowcount
            
            return result
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return None
        finally:
            cursor.close()
            connection.close()

db_manager = DatabaseManager()

def encode_vector_to_string(vector):
    """Chuyển đổi vector numpy thành string để lưu vào database"""
    if vector is None:
        return None
    if isinstance(vector, np.ndarray):
        # Chuyển numpy array thành list rồi encode base64
        vector_list = vector.tolist()
        vector_json = json.dumps(vector_list)
        return base64.b64encode(vector_json.encode()).decode()
    return vector

def decode_string_to_vector(vector_string):
    """Chuyển đổi string từ database thành vector numpy"""
    if not vector_string:
        return None
    try:
        # Decode base64 rồi chuyển thành numpy array
        vector_json = base64.b64decode(vector_string.encode()).decode()
        vector_list = json.loads(vector_json)
        return np.array(vector_list)
    except Exception as e:
        logger.error(f"Error decoding vector: {e}")
        return None

@app.route('/api/health', methods=['GET'])
def health_check():
    """Kiểm tra trạng thái API"""
    # Test database connection
    connection = db_manager.get_connection()
    db_status = "connected" if connection else "disconnected"
    if connection:
        connection.close()
    
    return jsonify({
        'success': True,
        'message': 'API đang hoạt động',
        'database_status': db_status,
        'database_host': DB_CONFIG['host'],
        'database_port': DB_CONFIG['port'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/student/search', methods=['GET'])
def search_student():
    """Tìm kiếm học sinh theo tên hoặc ID"""
    try:
        name = request.args.get('name', '')
        student_id = request.args.get('id', '')
        
        if not name and not student_id:
            return jsonify({
                'success': False,
                'message': 'Cần cung cấp tên hoặc ID để tìm kiếm'
            }), 400
        
        # Xây dựng query
        if student_id:
            query = "SELECT * FROM students WHERE id = %s"
            params = (student_id,)
        else:
            query = "SELECT * FROM students WHERE full_name LIKE %s"
            params = (f'%{name}%',)
        
        results = db_manager.execute_query(query, params)
        
        if results is None:
            return jsonify({
                'success': False,
                'message': 'Lỗi truy vấn database'
            }), 500
        
        # Chuyển đổi vector_face thành dạng có thể đọc được
        for student in results:
            if student['vector_face']:
                vector = decode_string_to_vector(student['vector_face'])
                if vector is not None:
                    student['vector_face_info'] = {
                        'has_vector': True,
                        'vector_size': len(vector),
                        'vector_shape': vector.shape if hasattr(vector, 'shape') else None
                    }
                else:
                    student['vector_face_info'] = {'has_vector': False}
            else:
                student['vector_face_info'] = {'has_vector': False}
        
        return jsonify({
            'success': True,
            'data': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({
            'success': False,
            'message': f'Lỗi server: {str(e)}'
        }), 500

@app.route('/api/student/update-vector', methods=['POST'])
def update_student_vector():
    """Cập nhật vector encode cho học sinh"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Không có dữ liệu được gửi'
            }), 400
        
        student_id = data.get('id')
        vector_data = data.get('vector_face')
        
        if not student_id:
            return jsonify({
                'success': False,
                'message': 'ID học sinh là bắt buộc'
            }), 400
        
        # Kiểm tra học sinh có tồn tại không
        check_query = "SELECT id FROM students WHERE id = %s"
        existing = db_manager.execute_query(check_query, (student_id,))
        
        if not existing:
            return jsonify({
                'success': False,
                'message': 'Không tìm thấy học sinh'
            }), 404
        
        # Xử lý vector data
        if vector_data:
            # Nếu vector_data là list, chuyển thành numpy array
            if isinstance(vector_data, list):
                vector_array = np.array(vector_data)
                encoded_vector = encode_vector_to_string(vector_array)
            else:
                encoded_vector = vector_data
        else:
            encoded_vector = None
        
        # Cập nhật vector
        update_query = "UPDATE students SET vector_face = %s WHERE id = %s"
        result = db_manager.execute_query(update_query, (encoded_vector, student_id), fetch=False)
        
        if result is None:
            return jsonify({
                'success': False,
                'message': 'Lỗi cập nhật database'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Cập nhật vector thành công',
            'updated_rows': result
        })
        
    except Exception as e:
        logger.error(f"Update vector error: {e}")
        return jsonify({
            'success': False,
            'message': f'Lỗi server: {str(e)}'
        }), 500

@app.route('/api/student/create', methods=['POST'])
def create_student():
    """Tạo học sinh mới"""
    try:
        data = request.get_json()
        
        if not data or not data.get('full_name'):
            return jsonify({
                'success': False,
                'message': 'Tên học sinh là bắt buộc'
            }), 400
        
        # Chuẩn bị dữ liệu
        full_name = data.get('full_name')
        code_student = data.get('code_student')
        phone = data.get('phone')
        address = data.get('address')
        email = data.get('email')
        vector_face = data.get('vector_face')
        
        # Xử lý vector
        if vector_face:
            if isinstance(vector_face, list):
                vector_array = np.array(vector_face)
                encoded_vector = encode_vector_to_string(vector_array)
            else:
                encoded_vector = vector_face
        else:
            encoded_vector = None
        
        # Tạo học sinh mới
        insert_query = """
            INSERT INTO students (full_name, code_student, phone, address, email, 
                                vector_face, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        current_time = int(datetime.now().timestamp())
        params = (full_name, code_student, phone, address, email, 
                 encoded_vector, 'active', current_time)
        
        result = db_manager.execute_query(insert_query, params, fetch=False)
        
        if result is None:
            return jsonify({
                'success': False,
                'message': 'Lỗi tạo học sinh'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Tạo học sinh thành công'
        })
        
    except Exception as e:
        logger.error(f"Create student error: {e}")
        return jsonify({
            'success': False,
            'message': f'Lỗi server: {str(e)}'
        }), 500

@app.route('/api/student/get-vector/<int:student_id>', methods=['GET'])
def get_student_vector(student_id):
    """Lấy vector encode của học sinh"""
    try:
        query = "SELECT id, full_name, vector_face FROM students WHERE id = %s"
        result = db_manager.execute_query(query, (student_id,))
        
        if not result:
            return jsonify({
                'success': False,
                'message': 'Không tìm thấy học sinh'
            }), 404
        
        student = result[0]
        
        # Chuyển đổi vector thành dạng có thể sử dụng
        if student['vector_face']:
            vector = decode_string_to_vector(student['vector_face'])
            if vector is not None:
                student['vector_face'] = vector.tolist()
            else:
                student['vector_face'] = None
        
        return jsonify({
            'success': True,
            'data': student
        })
        
    except Exception as e:
        logger.error(f"Get vector error: {e}")
        return jsonify({
            'success': False,
            'message': f'Lỗi server: {str(e)}'
        }), 500

@app.route('/api/student/list', methods=['GET'])
def list_students():
    """Lấy toàn bộ thông tin tất cả học sinh"""
    try:
        query = "SELECT * FROM students"
        results = db_manager.execute_query(query)
        
        if results is None:
            return jsonify({
                'success': False,
                'message': 'Lỗi truy vấn database'
            }), 500
        
        # Chuyển vector_face về dạng list nếu có
        for student in results:
            if student['vector_face']:
                vector = decode_string_to_vector(student['vector_face'])
                student['vector_face'] = vector.tolist() if vector is not None else None
        
        return jsonify({
            'success': True,
            'data': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"List students error: {e}")
        return jsonify({
            'success': False,
            'message': f'Lỗi server: {str(e)}'
        }), 500

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

@app.route('/api/face_vector_encode', methods=['GET'])
def encode_face_from_images_get():
    logger.warning("❌ [GET] /api/face_vector_encode được truy cập bằng GET thay vì POST.")
    return jsonify({
        'success': False,
        'message': 'Vui lòng sử dụng phương thức POST với dữ liệu JSON để truy cập API này.',
        'error_code': 405
    }), 405

@app.route('/api/face_vector_encode', methods=['POST'])
def encode_face_from_images():
    """API nhận 3 ảnh base64 và trả về vector trung bình nếu hợp lệ"""
    try:
        data = request.get_json()
        if not data:
            logger.warning("📭 Không có dữ liệu gửi lên (body rỗng hoặc sai định dạng).")
            return jsonify({'success': False, 'message': 'Không có dữ liệu gửi lên', 'error_code': 400}), 400


        image_front = data.get('image_front')
        image_left = data.get('image_left')
        image_right = data.get('image_right')

        # Nếu thiếu bất kỳ ảnh nào, chỉ xử lý mặt trước
        if not (image_front and image_left and image_right):
            logger.warning("⚠️ Không đủ 3 ảnh, chỉ xử lý ảnh mặt trước.")
            if not image_front:
                logger.warning("❌ Không có ảnh mặt trước.")
                return jsonify({'success': False, 'message': 'Thiếu ảnh mặt trước (image_front)', 'error_code': 411}), 400
            img = base64_to_image(image_front)
            if img is None:
                logger.warning("❌ Không đọc được ảnh mặt trước (base64 lỗi hoặc không phải ảnh).")
                return jsonify({'success': False, 'message': 'Không đọc được ảnh mặt trước, vui lòng tải lại.', 'error_code': 412}), 400
            logger.info(f"📏 Kích thước ảnh mặt trước: {img.shape}")
            faces = face_app.get(img)
            if not faces or faces[0].det_score < 0.7:
                score = faces[0].det_score if faces else 0
                logger.warning(f"❌ Không phát hiện khuôn mặt rõ ở ảnh mặt trước (score: {score:.3f})")
                return jsonify({'success': False, 'message': 'Không phát hiện khuôn mặt rõ ràng ở ảnh mặt trước, vui lòng tải lại.', 'error_code': 413}), 400
            face = faces[0]
            logger.info("✅ Ảnh mặt trước hợp lệ, đang lấy embedding...")
            avg_vector = face.embedding
            logger.info("✅ Đã lấy xong embedding từ ảnh mặt trước.")
            return jsonify({
                'success': True,
                'vector': avg_vector.tolist(),
                'fallback': True
            }), 200

        # Nếu đủ 3 ảnh, xử lý như cũ
        vectors = []
        for idx, base64_str in enumerate([image_front, image_left, image_right]):
            direction = ['front', 'left', 'right'][idx]
            logger.info(f"📥 Xử lý ảnh hướng: {direction.upper()}")
            img = base64_to_image(base64_str)
            if img is None:
                logger.warning(f"❌ Không đọc được ảnh {direction} (base64 lỗi hoặc không phải ảnh).")
                return jsonify({'success': False, 'message': f'Không đọc được ảnh thứ {idx+1} ({direction}), vui lòng tải lại.', 'error_code': 402}), 400
            logger.info(f"📏 Kích thước ảnh {direction}: {img.shape}")
            faces = face_app.get(img)
            if not faces or faces[0].det_score < 0.7:
                score = faces[0].det_score if faces else 0
                logger.warning(f"❌ Không phát hiện khuôn mặt rõ ở ảnh {direction} (score: {score:.3f})")
                return jsonify({'success': False, 'message': f'Không phát hiện khuôn mặt rõ ràng ở ảnh thứ {idx+1} ({direction}), vui lòng tải lại.', 'error_code': 403}), 400
            face = faces[0]
            logger.info(f"✅ Ảnh {direction.upper()} hợp lệ, đang lấy embedding...")
            vectors.append(face.embedding)
        avg_vector = np.mean(vectors, axis=0)
        logger.info("✅ Đã tính xong vector trung bình.")
        return jsonify({
            'success': True,
            'vector': avg_vector.tolist(),
            'fallback': False
        }), 200

    except Exception as e:
        logger.exception(f"🔥 Lỗi encode face: {e}")
        return jsonify({'success': False, 'message': f'Lỗi server: {str(e)}', 'error_code': 500}), 500

if __name__ == '__main__':
    print("Starting Face Recognition API Server...")
    print(f"Database Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"Database: {DB_CONFIG['database']}")
    print("Server running at: http://localhost:5002")
    app.run(debug=True, host='0.0.0.0', port=5002)
