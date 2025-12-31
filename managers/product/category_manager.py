# managers/product/category_manager.py
import uuid
import logging
from google.cloud import firestore

class CategoryManager:
    def __init__(self, db):
        self.db = db
        self.cat_col = self.db.collection('categories')

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

    def create_category(self, name, prefix):
        """Creates a new product category document in Firestore."""
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
            logging.info(f"Category {cat_id} created successfully.")
            return data
        except Exception as e:
            logging.error(f"Failed to create category '{name}': {e}")
            return None

    def get_categories(self):
        """Retrieves all categories from the Firestore collection."""
        return self._get_safe_list(self.cat_col)
