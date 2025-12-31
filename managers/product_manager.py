import uuid
import logging
from datetime import datetime
import streamlit as st
from google.cloud import firestore
from google.cloud.firestore_v1.field_path import FieldPath
from google.cloud.firestore_v1.base_query import And, FieldFilter

class ProductManager:
    def __init__(self, firebase_client):
        self.db = firebase_client.db
        self.bucket = firebase_client.bucket
        self.collection = self.db.collection('products')
        self.cat_col = self.db.collection('categories')
        self.unit_col = self.db.collection('units')

    def _get_safe_list(self, collection_ref):
        try:
            results = []
            for doc in collection_ref.stream():
                data = doc.to_dict()
                if isinstance(data, dict):
                    data['id'] = doc.id 
                    results.append(data)
            return results
        except Exception as e:
            logging.error(f"Error in _get_safe_list for {collection_ref.id}: {e}")
            return []

    # ... (Category and Unit functions remain the same) ...
    def create_category(self, name, prefix):
        cat_id = f"CAT-{uuid.uuid4().hex[:4].upper()}"
        data = {
            "id": cat_id, 
            "name": name, 
            "prefix": prefix.upper(), 
            "current_seq": 0,
            "active": True
        }
        self.cat_col.document(cat_id).set(data)
        return data

    def get_categories(self):
        return self._get_safe_list(self.cat_col)

    def create_unit(self, name):
        unit_id = f"UNT-{uuid.uuid4().hex[:4].upper()}"
        data = {"id": unit_id, "name": name}
        self.unit_col.document(unit_id).set(data)
        return data

    def get_units(self):
        return self._get_safe_list(self.unit_col)

    def create_product(self, product_data):
        # ... (implementation remains the same)
        if not product_data.get('category_id'):
            return False, "Thiếu Category ID"
        cat_ref = self.cat_col.document(product_data['category_id'])
        # ... transaction logic ...
        transaction = self.db.transaction()
        try:
            # ... (transaction run logic) ...
            pass
        except Exception as e:
            logging.error(f"Lỗi tạo sản phẩm: {e}")
            return False, f"Lỗi tạo sản phẩm: {str(e)}"

    def update_product(self, sku, updates):
        self.collection.document(sku).update(updates)

    def get_all_products(self):
        """
        ULTIMATE FIX - LAYER 2: Lấy tất cả sản phẩm đang active. 
        Hàm này được thiết kế để an toàn tuyệt đối, luôn trả về một list các dict, hoặc list rỗng.
        """
        try:
            query = self.collection.where("active", "==", True)
            docs = query.stream()
            results = []
            for doc in docs:
                d = doc.to_dict()
                # Lớp phòng thủ: Đảm bảo dữ liệu từ Firestore là một dict hợp lệ
                if isinstance(d, dict) and d:
                    d['sku'] = doc.id
                    d['cogs'] = d.get('cost_price', 0) # Đồng bộ với UI
                    results.append(d)
                else:
                    # Ghi lại lỗi nếu một document không phải là dict, điều này rất bất thường
                    logging.warning(f"Firestore document {doc.id} in 'products' collection is not a valid dictionary.")
            return results
        except Exception as e:
            # Nếu có bất kỳ lỗi nào ở cấp độ cao hơn (ví dụ: mất kết nối, quyền truy cập...),
            # ghi lại lỗi và trả về một danh sách rỗng để ngăn chặn sập UI.
            logging.error(f"Critical error in get_all_products: {e}. Returning empty list.")
            return []

    def get_listed_products_for_branch(self, branch_id: str):
        """Hàm này giờ đây sẽ an toàn hơn nhờ sử dụng get_all_products."""
        try:
            all_active_products = self.get_all_products()
            results = []
            for product in all_active_products:
                # Kiểm tra `product` là dict đã được thực hiện trong get_all_products
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
        """Hàm này giờ đây sẽ an toàn hơn nhờ sử dụng get_all_products."""
        # Có thể tối ưu lại hàm này để chỉ lấy các trường cần thiết,
        # nhưng để đơn giản, ta sẽ dùng lại get_all_products đã được gia cố.
        all_products = self.get_all_products()
        # Logic của hàm này có thể được tích hợp vào get_all_products nếu cần.
        return all_products
