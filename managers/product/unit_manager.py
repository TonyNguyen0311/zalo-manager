# managers/product/unit_manager.py
import uuid
import logging
from google.cloud import firestore

class UnitManager:
    def __init__(self, db):
        self.db = db
        self.unit_col = self.db.collection('units')

    def create_unit(self, name):
        try:
            unit_id = f"UNT-{uuid.uuid4().hex[:4].upper()}"
            data = {
                "id": unit_id, 
                "name": name,
                "created_at": firestore.SERVER_TIMESTAMP
            }
            self.unit_col.document(unit_id).set(data)
            return True, f"Tạo đơn vị '{name}' thành công!"
        except Exception as e:
            logging.error(f"Failed to create unit '{name}': {e}")
            return False, f"Lỗi: {e}"

    def get_units(self):
        try:
            docs = self.unit_col.order_by("name").stream()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logging.error(f"Error getting units: {e}")
            return []

    def delete_unit(self, unit_id):
        try:
            # TODO: Check if unit is in use before deleting
            self.unit_col.document(unit_id).delete()
            return True, "Xóa đơn vị thành công."
        except Exception as e:
            logging.error(f"Error deleting unit {unit_id}: {e}")
            return False, f"Lỗi: {e}"