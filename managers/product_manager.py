import uuid
from datetime import datetime
import streamlit as st
from google.cloud import firestore

class ProductManager:
    def __init__(self, firebase_client):
        self.db = firebase_client.db
        self.bucket = firebase_client.bucket
        self.collection = self.db.collection('products')
        self.cat_col = self.db.collection('categories')
        self.unit_col = self.db.collection('units')

    # --- XỬ LÝ ẢNH ---
    def upload_image(self, file_obj, filename):
        if not self.bucket: return None
        try:
            path = f"products/{int(datetime.now().timestamp())}_{filename}"
            blob = self.bucket.blob(path)
            blob.upload_from_file(file_obj, content_type=file_obj.type)
            blob.make_public()
            return blob.public_url
        except Exception as e:
            print(f"Upload error: {e}")
            return None

    # --- HELPER: LẤY DATA AN TOÀN ---
    def _get_safe_list(self, collection_ref):
        """Helper để lấy list document và tự fill ID nếu thiếu"""
        results = []
        for doc in collection_ref.stream():
            data = doc.to_dict()
            # Luôn đảm bảo có field 'id' lấy từ document ID
            data['id'] = doc.id 
            results.append(data)
        return results

    # --- DANH MỤC ---
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
        # SỬ DỤNG HÀM AN TOÀN
        return self._get_safe_list(self.cat_col)

    # --- ĐƠN VỊ TÍNH ---
    def create_unit(self, name):
        unit_id = f"UNT-{uuid.uuid4().hex[:4].upper()}"
        data = {"id": unit_id, "name": name}
        self.unit_col.document(unit_id).set(data)
        return data

    def get_units(self):
        # SỬ DỤNG HÀM AN TOÀN -> Fix lỗi KeyError: 'id'
        return self._get_safe_list(self.unit_col)

# --- SẢN PHẨM ---
    def create_product(self, product_data):
        transaction = self.db.transaction()
        # Đảm bảo category_id hợp lệ
        if not product_data.get('category_id'):
            return False, "Thiếu Category ID"
            
        cat_ref = self.cat_col.document(product_data['category_id'])

        try:
            # SỬA LẠI DÒNG NÀY: Truyền product_data như một tham số bình thường sau cat_ref
            return self._create_product_transaction(transaction, cat_ref, product_data)
        except Exception as e:
            return False, f"Lỗi tạo sản phẩm: {str(e)}"

    # GIỮ NGUYÊN DECORATOR VÀ THAM SỐ
    @firestore.transactional
    def _create_product_transaction(self, transaction, cat_ref, product_data):
        snapshot = cat_ref.get(transaction=transaction)
        if not snapshot.exists:
            raise Exception("Danh mục không tồn tại!")
        
        cat_data = snapshot.to_dict()
        prefix = cat_data.get('prefix', 'SP')
        current_seq = cat_data.get('current_seq', 0)
        
        new_seq = current_seq + 1
        new_sku = f"{prefix}-{new_seq:04d}"
        
        prod_ref = self.collection.document(new_sku)
        if prod_ref.get(transaction=transaction).exists:
            raise Exception(f"SKU {new_sku} đã tồn tại. Vui lòng thử lại.")

        transaction.update(cat_ref, {"current_seq": new_seq})

        product_data['sku'] = new_sku
        product_data['created_at'] = datetime.now().isoformat()
        product_data['active'] = True
        
        transaction.set(prod_ref, product_data)
        return True, f"Tạo thành công: {new_sku}"

    def update_product(self, sku, updates):
        self.collection.document(sku).update(updates)

    def get_all_products(self):
        # Chỉ lấy sản phẩm active
        docs = self.collection.where("active", "==", True).stream()
        results = []
        for doc in docs:
            d = doc.to_dict()
            d['sku'] = doc.id # Đảm bảo có sku
            results.append(d)
        return results
            
    def delete_product(self, sku):
        self.collection.document(sku).update({"active": False})
