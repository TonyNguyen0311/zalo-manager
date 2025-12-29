import uuid
from datetime import datetime

class BranchManager:
    def __init__(self, firebase_client):
        self.db = firebase_client.db
        self.collection = self.db.collection('branches')

    def create_branch(self, name, address, phone):
        """Tạo chi nhánh mới"""
        # Tự động sinh ID kiểu BR-xxxx (hoặc dùng UUID cho đơn giản)
        branch_id = f"BR-{uuid.uuid4().hex[:6].upper()}"
        
        data = {
            "id": branch_id,
            "name": name,
            "address": address,
            "phone": phone,
            "active": True,
            "created_at": datetime.now().isoformat()
        }
        # Dùng set với document ID là branch_id để dễ truy vấn sau này
        self.collection.document(branch_id).set(data)
        return data

    def get_all_branches(self):
        """Lấy danh sách tất cả chi nhánh"""
        docs = self.collection.stream()
        return [doc.to_dict() for doc in docs]

    def get_branch(self, branch_id):
        doc = self.collection.document(branch_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
