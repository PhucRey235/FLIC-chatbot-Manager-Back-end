# app.py
from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
from model.database import preprocess_file, initialize_mongodb  # Giả sử database.py cùng cấp với app.py
from flask_cors import CORS
from flask import g

# python app.py

# Nạp biến môi trường từ file .env để lấy thông tin cấu hình như MONGODB_URI
load_dotenv()
MONGODB_URI = os.getenv('MONGODB_URI')  # Lấy chuỗi kết nối MongoDB từ biến môi trường

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
CORS(app)


def get_db():
    if 'client' not in g:
        g.client = initialize_mongodb()
        g.db = g.client['flic_chatbot']
        g.collection = g.db['documents']
    return g.collection

@app.teardown_appcontext
def close_db(exception):
    client = g.pop('client', None)
    if client is not None:
        client.close()
        
# Định nghĩa endpoint POST để upload file lên MongoDB
@app.route('/api/upload', methods=['POST'])
def upload_file():
    
    if 'collection' not in g:
        g.collection = get_db()  # Đảm bảo đã kết nối MongoDB
    
    collection = g.collection
    
    # Kiểm tra xem collection có tồn tại không, nếu không trả về lỗi 500
    if collection is None:
        return jsonify({'error': 'Không thể kết nối đến MongoDB'}), 500
    
    try:
        # Kiểm tra xem request có chứa file không, nếu không trả về lỗi 400
        if 'file' not in request.files:
            return jsonify({'error': 'Không có file được gửi lên'}), 400
        
        # Lấy file từ request và mô tả (nếu có) từ form data
        file = request.files['file']
        description = request.form.get('description', '')  # Mặc định là chuỗi rỗng nếu không có mô tả
        
        # Kiểm tra xem file có tên không, nếu không trả về lỗi 400
        if file.filename == '':
            return jsonify({'error': 'Không có file được chọn'}), 400
        
        # Tiền xử lý file bằng hàm preprocess_file để tạo document cho MongoDB
        result, response = preprocess_file(file, request, description)
        
        collection.insert_many(result)
        
        # Trả về thông tin file đã upload dưới dạng JSON với mã trạng thái 200
        return jsonify(response), 200
    
    # Xử lý ngoại lệ nếu có lỗi xảy ra trong quá trình upload
    except Exception as e:
        print(f"Error: {str(e)}")  # In lỗi ra console để debug
        return jsonify({'error': str(e)}), 500  # Trả về lỗi 500 với thông tin chi tiết

# Định nghĩa endpoint GET để lấy danh sách các tài liệu từ MongoDB
@app.route('/api/files', methods=['GET'])
def list_files():
    if 'collection' not in g:
        g.collection = get_db()  # Đảm bảo đã kết nối MongoDB
    
    collection = g.collection
    
    # Kiểm tra xem collection có tồn tại không, nếu không trả về lỗi 500
    if collection is None:
        return jsonify({'error': 'Không thể kết nối đến MongoDB'}), 500
    
    try:
        # Lấy tất cả document từ collection, loại bỏ field '_id' gốc
        documents = list(g.collection.find({}, {'_id': 0}))
        # Duyệt qua từng document để chuyển '_id' thành 'id' dạng chuỗi
        for doc in documents:
            doc['id'] = str(doc.pop('_id')) if '_id' in doc else doc.get('id')
        # Trả về danh sách file dưới dạng JSON với mã trạng thái 200
        return jsonify({'files': documents}), 200
    # Xử lý ngoại lệ nếu có lỗi xảy ra trong quá trình lấy danh sách
    except Exception as e:
        print(f"Error: {str(e)}")  # In lỗi ra console
        return jsonify({'error': str(e)}), 500  # Trả về lỗi 500

# Định nghĩa endpoint DELETE để xóa một tài liệu dựa trên tên file
@app.route('/api/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    
    if 'collection' not in g:
        g.collection = get_db()  # Đảm bảo đã kết nối MongoDB
    
    collection = g.collection
    
    # Kiểm tra xem collection có tồn tại không, nếu không trả về lỗi 500
    if collection is None:
        return jsonify({'error': 'Không thể kết nối đến MongoDB'}), 500
    
    try:
        # Xóa document có trường 'name' khớp với filename
        result = g.collection.delete_one({'name': filename})
        # Kiểm tra xem có document nào bị xóa không
        if result.deleted_count == 0:
            return jsonify({'error': 'File không tồn tại'}), 404  # Trả về lỗi 404 nếu không tìm thấy
        # Trả về thông báo thành công với mã trạng thái 200
        return jsonify({'message': f'Đã xóa file {filename}'}), 200
    # Xử lý ngoại lệ nếu có lỗi xảy ra trong quá trình xóa
    except Exception as e:
        print(f"Error: {str(e)}")  # In lỗi ra console
        return jsonify({'error': str(e)}), 500  # Trả về lỗi 500

# Khởi động ứng dụng Flask nếu kết nối MongoDB thành công
if __name__ == '__main__':
    # Chạy ứng dụng ở chế độ debug, lắng nghe trên tất cả IP, port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)
