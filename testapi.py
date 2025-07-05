import requests
import json
import numpy as np
import urllib3

# Vô hiệu hóa SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Cấu hình API - SỬA LẠI
API_BASE_URL = "https://python.topcam.ai.vn/api"

def test_health_check():
    """Kiểm tra trạng thái API"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", verify=False)
        print("=== Health Check ===")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"Health check error: {e}")
        return False

def test_search_student():
    """Test tìm kiếm sinh viên"""
    print("=== Search Student ===")
    
    # Tìm theo tên
    response = requests.get(f"{API_BASE_URL}/student/search", 
                          params={"name": "Trần Mạnh"}, verify=False)
    print(f"Search by name - Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    
    # Tìm theo ID
    response = requests.get(f"{API_BASE_URL}/student/search", 
                          params={"id": "1"}, verify=False)
    print(f"Search by ID - Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_update_vector():
    """Test cập nhật vector"""
    print("=== Update Vector ===")
    
    # Tạo vector giả
    fake_vector = np.random.rand(128).tolist()
    
    data = {
        "id": 1,
        "vector_face": fake_vector
    }
    
    response = requests.post(f"{API_BASE_URL}/student/update-vector", 
                           json=data, verify=False)
    print(f"Update vector - Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_get_vector():
    """Test lấy vector"""
    print("=== Get Vector ===")
    
    response = requests.get(f"{API_BASE_URL}/student/get-vector/1", verify=False)
    print(f"Get vector - Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_create_student():
    """Test tạo sinh viên mới"""
    print("=== Create Student ===")
    
    fake_vector = np.random.rand(128).tolist()
    
    data = {
        "full_name": "Nguyễn Văn Test",
        "code_student": "TEST001",
        "phone": "0123456789",
        "address": "Hà Nội",
        "email": "test@example.com",
        "vector_face": fake_vector
    }
    
    response = requests.post(f"{API_BASE_URL}/student/create", 
                           json=data, verify=False)
    print(f"Create student - Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_list_students():
    """Test lấy danh sách sinh viên"""
    print("=== List Students ===")
    
    response = requests.get(f"{API_BASE_URL}/student/list", verify=False)
    print(f"List students - Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

if __name__ == "__main__":
    print("Testing Face Recognition API...")
    print(f"API URL: {API_BASE_URL}")
    print("="*50)
    
    # Test health check
    if not test_health_check():
        print("API không hoạt động. Vui lòng kiểm tra server.")
        exit(1)
    
    # Test các chức năng
    test_search_student()
    test_update_vector()
    test_get_vector()
    test_create_student()
    test_list_students()
    
    print("Test completed!")