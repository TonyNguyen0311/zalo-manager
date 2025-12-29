import firebase_admin
from firebase_admin import credentials, firestore, storage
import json
import streamlit as st

class FirebaseClient:
    def __init__(self, credentials_input, storage_bucket=None):
        """
        Khởi tạo kết nối Firebase.
        :param credentials_input: Có thể là dict (từ st.secrets) hoặc đường dẫn file str.
        :param storage_bucket: Tên bucket storage (ví dụ: 'app.appspot.com').
        """
        # Kiểm tra xem app đã khởi tạo chưa để tránh lỗi initialize lại
        if not firebase_admin._apps:
            # Xử lý credential
            if isinstance(credentials_input, dict):
                # Nếu truyền vào là dict (lấy từ st.secrets)
                cred = credentials.Certificate(credentials_input)
            else:
                # Nếu truyền vào là đường dẫn file (khi chạy local test)
                cred = credentials.Certificate(credentials_input)

            options = {}
            if storage_bucket:
                options['storageBucket'] = storage_bucket

            firebase_admin.initialize_app(cred, options)

        # Khởi tạo clients
        self.db = firestore.client()
        self.bucket = storage.bucket() if storage_bucket else None
        
    def check_connection(self):
        """Hàm test kết nối đơn giản"""
        try:
            # Thử lấy thời gian server hoặc list collections
            # Ở đây ta chỉ check đơn giản object db tồn tại
            if self.db:
                return True
            return False
        except Exception as e:
            st.error(f"Lỗi kết nối Firebase: {e}")
            return False
