import bcrypt
import uuid
from datetime import datetime
import streamlit as st

class AuthManager:
    def __init__(self, firebase_client):
        self.db = firebase_client.db
        self.collection = self.db.collection('users')

    def _hash_password(self, password):
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def _check_password(self, password, hashed):
        return bcrypt.checkpw(password.encode(), hashed.encode())

    def create_user(self, username, password, role, branch_id, display_name):
        # Kiểm tra username đã tồn tại chưa
        existing = self.collection.where("username", "==", username).get()
        if existing:
            return False, "Username đã tồn tại"

        user_id = f"U-{uuid.uuid4().hex[:6].upper()}"
        data = {
            "id": user_id,
            "username": username,
            "password_hash": self._hash_password(password),
            "role": role,         # ADMIN / STAFF
            "branch_id": branch_id,
            "display_name": display_name,
            "created_at": datetime.now().isoformat(),
            "active": True
        }
        self.collection.document(user_id).set(data)
        return True, data

    def login(self, username, password):
        # Tìm user theo username
        docs = self.collection.where("username", "==", username).limit(1).get()
        
        if not docs:
            return None
        
        user_data = docs[0].to_dict()
        
        if not user_data.get('active', True):
            return None # User bị khóa
            
        if self._check_password(password, user_data['password_hash']):
            # Update last login
            self.collection.document(user_data['id']).update({
                "last_login": datetime.now().isoformat()
            })
            return user_data
        return None

    def has_users(self):
        """Kiểm tra xem hệ thống đã có user nào chưa (để setup lần đầu)"""
        # Lấy thử 1 document
        docs = self.collection.limit(1).get()
        return len(docs) > 0
