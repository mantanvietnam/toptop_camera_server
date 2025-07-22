import mysql.connector
from flask import Flask, request, jsonify
import json
import base64
import numpy as np
from datetime import datetime
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Cấu hình database - CẬP NHẬT
DB_CONFIG = {
    'host': '0.0.0.0',
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

if __name__ == '__main__':
    print("Starting Face Recognition API Server...")
    print(f"Database Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"Database: {DB_CONFIG['database']}")
    print("Server running at: http://localhost:5002")
    app.run(debug=True, host='0.0.0.0', port=5002)
