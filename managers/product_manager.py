# managers/product_manager.py
import uuid
import logging
from google.cloud import firestore
from google.cloud.firestore_v1.field_path import FieldPath
from google.cloud.firestore_v1.base_query import And, FieldFilter

# Import the sub-managers
from .product.category_manager import CategoryManager
from .product.unit_manager import UnitManager
# Note: We no longer initialize ImageHandler here, it's passed in.

class ProductManager:
    # MODIFIED: __init__ now accepts an image_handler instance
    def __init__(self, firebase_client, image_handler=None):
        self.db = firebase_client.db
        self.collection = self.db.collection('products')
        
        # Initialize sub-managers
        self.category_manager = CategoryManager(self.db)
        self.unit_manager = UnitManager(self.db)
        
        # MODIFIED: Assign the pre-configured image_handler
        self.image_handler = image_handler 

    # --- Method Delegation --- 
    # Delegate category and unit methods to their respective managers
    def get_categories(self):
        return self.category_manager.get_categories()

    def create_category(self, name, prefix):
        return self.category_manager.create_category(name, prefix)

    def get_units(self):
        return self.unit_manager.get_units()

    def create_unit(self, name):
        return self.unit_manager.create_unit(name)

    # Delegate image upload to the image handler
    def upload_image(self, file_obj, filename):
        # This now calls the Google Drive uploader if it was passed in
        if self.image_handler:
            return self.image_handler.optimize_and_upload_image(file_obj, filename)
        else:
            logging.warning("Image Handler not configured. Image upload skipped.")
            return None

    # --- Core Product Logic (Remains in ProductManager) ---

    def create_product(self, product_data):
        if not product_data.get('category_id'):
            return False, "Thiếu ID danh mục."

        cat_ref = self.category_manager.cat_col.document(product_data['category_id'])
        
        # Use a transaction to ensure atomic update of the category sequence and product creation
        transaction = self.db.transaction()
        
        @firestore.transactional
        def update_in_transaction(trans, cat_ref, product_data):
            try:
                cat_snapshot = trans.get(cat_ref, field_paths=["prefix", "current_seq"])[0].to_dict()
                
                prefix = cat_snapshot.get("prefix", "PRD")
                current_seq = cat_snapshot.get("current_seq", 0)
                new_seq = current_seq + 1
                
                # Generate the new SKU
                sku = f"{prefix}{str(new_seq).zfill(6)}"
                product_data['sku'] = sku
                product_data['active'] = True
                product_data['created_at'] = firestore.SERVER_TIMESTAMP

                # Create the new product document
                product_ref = self.collection.document(sku)
                trans.set(product_ref, product_data)
                
                # Update the sequence number in the category document
                trans.update(cat_ref, {"current_seq": new_seq})
                
                return sku, None
            except Exception as e:
                # This will cause the transaction to fail and roll back
                logging.error(f"Transaction failed during product creation: {e}")
                raise e # Re-raise to ensure transaction rollback

        try:
            sku, error = update_in_transaction(transaction, cat_ref, product_data)
            if error:
                return False, error
            logging.info(f"Product {sku} created successfully.")
            return True, sku
        except Exception as e:
            return False, f"Lỗi khi tạo sản phẩm: {str(e)}"

    def update_product(self, sku, updates):
        self.collection.document(sku).update(updates)

    def get_all_products(self):
        """Fetches all active products. This is a foundational, safe method."""
        try:
            query = self.collection.where(filter=FieldFilter("active", "==", True))
            docs = query.stream()
            results = []
            for doc in docs:
                d = doc.to_dict()
                if isinstance(d, dict):
                    d['sku'] = doc.id
                    results.append(d)
                else:
                    logging.warning(f"Firestore document {doc.id} in 'products' collection is not a valid dict.")
            return results
        except Exception as e:
            logging.error(f"Critical error in get_all_products: {e}")
            return []

    def get_listed_products_for_branch(self, branch_id: str):
        """Gets products listed for a specific branch, using the safer get_all_products."""
        try:
            all_active_products = self.get_all_products()
            results = []
            for product in all_active_products:
                price_info = product.get('price_by_branch', {}).get(branch_id)
                if isinstance(price_info, dict) and price_info.get('active') is True:
                    results.append(product)
            return results
        except Exception as e:
            logging.error(f"Error in get_listed_products_for_branch for {branch_id}: {e}")
            return []

    def delete_product(self, sku):
        self.collection.document(sku).update({"active": False})

    def get_all_products_with_cost(self):
        return self.get_all_products()
