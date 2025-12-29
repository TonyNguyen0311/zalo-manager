import firebase_admin
from firebase_admin import credentials, firestore
import json
import streamlit as st

class FirebaseClient:
    def __init__(self, credentials_input, storage_bucket=None):
        """
        Khởi tạo kết nối Firebase (Chỉ dùng Firestore, bỏ qua Storage).
        """
        if not firebase_admin._apps:
            if isinstance(credentials_input, dict):
                cred = credentials.Certificate(credentials_input)
            else:
                cred = credentials.Certificate(credentials_input)

            # Bỏ phần options storageBucket
            firebase_admin.initialize_app(cred)

        # Chỉ khởi tạo DB
        self.db = firestore.client()
        self.bucket = None # Tắt Storage
        
    def check_connection(self):
        try:
            if self.db:
                return True
            return False
        except Exception as e:
            st.error(f"Lỗi kết nối Firebase: {e}")
            return False
