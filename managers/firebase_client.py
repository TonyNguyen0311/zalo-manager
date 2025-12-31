import firebase_admin
from firebase_admin import credentials, firestore, storage # Import storage
import pyrebase
import json
import streamlit as st

class FirebaseClient:
    def __init__(self, credentials_input, pyrebase_config, storage_bucket=None):
        """
        Khởi tạo kết nối Firebase, bao gồm Firestore (admin), Auth (pyrebase), và Storage.
        """
        # --- Khởi tạo Firebase Admin SDK (cho Firestore & Storage) ---
        if not firebase_admin._apps:
            if isinstance(credentials_input, dict):
                cred = credentials.Certificate(credentials_input)
            else:
                # This path is relative to the app's root directory
                cred = credentials.Certificate(credentials_input)
            
            # Thêm cấu hình storage bucket nếu được cung cấp
            app_options = {}
            if storage_bucket:
                app_options['storageBucket'] = storage_bucket
            
            firebase_admin.initialize_app(cred, app_options)

        self.db = firestore.client()
        
        # Khởi tạo bucket nếu tên được cung cấp
        if storage_bucket:
            self.bucket = storage.bucket()
        else:
            self.bucket = None
            st.warning("Firebase Storage chưa được cấu hình. Chức năng upload file sẽ bị vô hiệu hóa.")
        
        # --- Khởi tạo Pyrebase (cho Authentication) ---
        # Pyrebase tự quản lý việc khởi tạo app của riêng nó
        firebase = pyrebase.initialize_app(pyrebase_config)
        self.auth = firebase.auth()

    def check_connection(self):
        try:
            # Chỉ cần kiểm tra db và auth là đủ
            if self.db and self.auth:
                return True
            return False
        except Exception as e:
            st.error(f"Lỗi kết nối Firebase: {e}")
            return False
