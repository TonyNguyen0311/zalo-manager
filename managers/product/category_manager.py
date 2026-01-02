# managers/product/category_manager.py
import uuid
import logging
from google.cloud import firestore

class CategoryManager:
    def __init__(self, db):
        self.db = db
        self.cat_col = self.db.collection('categories')

    def create_category(self, name, prefix):
        try:
            cat_id = f"CAT-{uuid.uuid4().hex[:4].upper()}"
            data = {
                "id": cat_id, 
                "name": name, 
                "prefix": prefix.upper(), 
                "current_seq": 0,
                "active": True,
                "created_at": firestore.SERVER_TIMESTAMP
            }
            self.cat_col.document(cat_id).set(data)
            return True, f"Tạo danh mục '{name}' thành công!"
        except Exception as e:
            logging.error(f"Failed to create category '{name}': {e}")
            return False, f"Lỗi: {e}"

    def get_categories(self):
        try:
            docs = self.cat_col.order_by("name").stream()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logging.error(f"Error getting categories: {e}")
            return []

    def delete_category(self, cat_id):
        try:
            # TODO: Check if category is in use before deleting
            self.cat_col.document(cat_id).delete()
            return True, "Xóa danh mục thành công."
        except Exception as e:
            logging.error(f"Error deleting category {cat_id}: {e}")
            return False, f"Lỗi: {e}"