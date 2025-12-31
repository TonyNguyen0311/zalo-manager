# managers/product/unit_manager.py
import uuid
import logging
from google.cloud import firestore

class UnitManager:
    def __init__(self, db):
        self.db = db
        self.unit_col = self.db.collection('units')

    def _get_safe_list(self, collection_ref):
        """Safely streams documents and returns a list of dictionaries, including document ID."""
        try:
            results = []
            for doc in collection_ref.stream():
                data = doc.to_dict()
                if isinstance(data, dict):
                    data['id'] = doc.id
                    results.append(data)
            return results
        except Exception as e:
            logging.error(f"Error fetching collection {collection_ref.id}: {e}")
            return []

    def create_unit(self, name):
        """Creates a new product unit document in Firestore."""
        try:
            unit_id = f"UNT-{uuid.uuid4().hex[:4].upper()}"
            data = {
                "id": unit_id, 
                "name": name,
                "created_at": firestore.SERVER_TIMESTAMP
            }
            self.unit_col.document(unit_id).set(data)
            logging.info(f"Unit {unit_id} created successfully.")
            return data
        except Exception as e:
            logging.error(f"Failed to create unit '{name}': {e}")
            return None

    def get_units(self):
        """Retrieves all units from the Firestore collection."""
        return self._get_safe_list(self.unit_col)
