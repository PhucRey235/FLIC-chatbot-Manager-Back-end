# model/database.py
# --- IMPORT CÁC THƯ VIỆN CẦN THIẾT ---
import os  # Thư viện xử lý thao tác hệ thống (đọc biến môi trường)
from dotenv import load_dotenv  # Nạp biến môi trường từ file .env
from pymongo import MongoClient  # Kết nối đến MongoDB
from pymongo.server_api import ServerApi  # Định nghĩa API server cho MongoDB
from datetime import datetime
from werkzeug.utils import secure_filename
from unidecode import unidecode
from langchain_experimental.text_splitter import SemanticChunker
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import uuid

# Nạp biến môi trường từ file .env (chỉ cần gọi một lần)
load_dotenv()
MONGODB_URI = os.getenv('MONGODB_URI')  # URI để kết nối MongoDB
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
EMBEDDING_MODEL = 'models/text-embedding-004'

# Khởi tạo kết nối MongoDB
def initialize_mongodb():
    try:
        client = MongoClient(MONGODB_URI, server_api=ServerApi('1'), serverSelectionTimeoutMS=5000)
        client.admin.command('ping')  # Kiểm tra kết nối
        return client
    except Exception as e:
        print(f"Không thể kết nối MongoDB: {str(e)}")
        return False

def initialize_embedding(model_name: str = EMBEDDING_MODEL) -> GoogleGenerativeAIEmbeddings:
    # Khởi tạo embedding model của Google Gemini một lần duy nhất
    embeddings = GoogleGenerativeAIEmbeddings(
        model=model_name,  # Sử dụng mô hình embedding-004
        google_api_key=GOOGLE_API_KEY
    )
    return embeddings

# Khởi tạo embedding model toàn cục
embeddings = initialize_embedding()

def create_chunker(embeddings_model) -> SemanticChunker:
    # Tạo SemanticChunker với các tham số tối ưu cho hiệu suất
    semantic_chunker = SemanticChunker(
        embeddings=embeddings_model,
        buffer_size=1,  # Tối thiểu hóa bộ đệm để tăng tốc độ
        breakpoint_threshold_type='percentile',  # Phương pháp phân chia tối ưu cho văn bản chung
        breakpoint_threshold_amount=90,  # Ngưỡng cao hơn để giảm số chunk nhỏ
        min_chunk_size=100  # Giữ kích thước chunk tối thiểu để tránh phân mảnh quá mức
    )
    return semantic_chunker

# Hàm tiền xử lý dữ liệu trước khi upload
def preprocess_file(file, request, description):
    # Đọc nội dung file dưới dạng UTF-8 (cần xử lý thêm nếu là PDF/DOCX)
    content = file.read().decode('utf-8')
    
    # Chuyển tên file thành không dấu trước khi bảo mật
    filename = secure_filename(unidecode(file.filename))
    
    results = []
    
    # Tạo chunker một lần duy nhất để xử lý nội dung
    semantic_chunker = create_chunker(embeddings)
    chunks = semantic_chunker.split_text(content)
    
    for chunk in chunks:
        embedding_context = embeddings.embed_query(chunk)
    
        # Tạo document hoàn chỉnh để lưu vào MongoDB
        results.append({
            'chunk_id': str(uuid.uuid4()),
            'name': filename,
            'size': file.content_length / 1024,  # Kích thước file tính bằng KB
            'type': file.mimetype,
            'uploadDate': datetime.now().strftime('%d/%m/%Y'),
            'description': description,
            'lastModified': request.form.get('lastModified', None),  # Lấy từ frontend nếu có
            'context': chunk,
            'embedding': embedding_context,  # Gọi embedding trực tiếp
            'chunk_length': len(chunk),
            'created_at': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),  # UTC để đồng bộ
        })
        
    respone = {
        'name': filename,
        'size': file.content_length / 1024,
        'type': file.mimetype,
        'uploadDate': datetime.now().strftime('%d/%m/%Y'),
        'description': description,
        'message': 'Tải lên thành công'
    }
    
    return results, respone