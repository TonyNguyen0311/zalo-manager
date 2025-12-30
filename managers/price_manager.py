
from datetime import datetime

class PriceManager:
    def __init__(self, firebase_client):
        self.db = firebase_client.db
        self.prices_col = self.db.collection('branch_prices')

    def set_price(self, sku: str, branch_id: str, price: float):
        """Tạo hoặc cập nhật giá bán cho một SKU tại một chi nhánh."""
        if not all([sku, branch_id, price >= 0]):
            raise ValueError("Thông tin SKU, chi nhánh và giá là bắt buộc.")
        
        doc_id = f"{branch_id}_{sku}"
        doc_ref = self.prices_col.document(doc_id)
        
        doc_ref.set({
            'branch_id': branch_id,
            'sku': sku,
            'price': price,
            'updated_at': datetime.now().isoformat()
        }, merge=True) # Dùng merge=True để không ghi đè trạng thái is_active

    def set_business_status(self, sku: str, branch_id: str, is_active: bool):
        """Thiết lập trạng thái kinh doanh (Đang bán/Tạm ngưng) cho sản phẩm."""
        doc_id = f"{branch_id}_{sku}"
        self.prices_col.document(doc_id).set({
            'is_active': is_active,
            'updated_at': datetime.now().isoformat()
        }, merge=True)

    def get_all_prices(self):
        """Lấy toàn bộ các bản ghi giá từ database."""
        docs = self.prices_col.stream()
        return [doc.to_dict() for doc in docs]

    def get_prices_for_branch(self, branch_id: str):
        """Lấy tất cả các bản ghi giá của một chi nhánh cụ thể."""
        docs = self.prices_col.where('branch_id', '==', branch_id).stream()
        return [doc.to_dict() for doc in docs]
    
    def get_active_prices_for_branch(self, branch_id: str):
        """Lấy các sản phẩm đang được 'Kinh doanh' tại một chi nhánh (cho POS)."""
        docs = self.prices_col.where('branch_id', '==', branch_id).where('is_active', '==', True).stream()
        return [doc.to_dict() for doc in docs]

    def get_price(self, sku: str, branch_id: str):
        """Lấy thông tin giá và trạng thái của một sản phẩm tại một chi nhánh."""
        doc_id = f"{branch_id}_{sku}"
        doc = self.prices_col.document(doc_id).get()
        if doc.exists:
            return doc.to_dict()
        return None

