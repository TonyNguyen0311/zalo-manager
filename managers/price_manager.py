
from datetime import datetime, time
import uuid

class PriceManager:
    def __init__(self, firebase_client):
        self.db = firebase_client.db
        self.prices_col = self.db.collection('branch_prices')
        self.schedules_col = self.db.collection('price_schedules') # <<< COLLECTION MỚI

    # --- CÁC HÀM QUẢN LÝ GIÁ TRỰC TIẾP (GIỮ NGUYÊN) ---
    def set_price(self, sku: str, branch_id: str, price: float):
        """Tạo hoặc cập nhật giá bán cho một SKU tại một chi nhánh."""
        if not all([sku, branch_id, price >= 0]):
            raise ValueError("Thông tin SKU, chi nhánh và giá là bắt buộc.")
        doc_id = f"{branch_id}_{sku}"
        self.prices_col.document(doc_id).set({
            'branch_id': branch_id,
            'sku': sku,
            'price': price,
            'updated_at': datetime.now().isoformat()
        }, merge=True)

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

    def get_active_prices_for_branch(self, branch_id: str):
        """Lấy các sản phẩm đang được 'Kinh doanh' tại một chi nhánh (cho POS)."""
        docs = self.prices_col.where('branch_id', '==', branch_id).where('is_active', '==', True).stream()
        return [doc.to_dict() for doc in docs]

    def get_price(self, sku: str, branch_id: str):
        """Lấy thông tin giá và trạng thái của một sản phẩm tại một chi nhánh."""
        doc = self.prices_col.document(f"{branch_id}_{sku}").get()
        return doc.to_dict() if doc.exists else None

    # --- CÁC HÀM MỚI CHO LỊCH TRÌNH GIÁ ---

    def schedule_price_change(self, sku: str, branch_id: str, new_price: float, apply_date: datetime, created_by: str):
        """Tạo một lịch trình thay đổi giá trong tương lai."""
        if not all([sku, branch_id, new_price > 0, apply_date, created_by]):
            return False, "Dữ liệu không hợp lệ."
        
        # Kết hợp ngày với thời gian đầu ngày (00:00:00) để đảm bảo tính nhất quán
        apply_datetime = datetime.combine(apply_date, time.min)

        schedule_id = f"SCH-{uuid.uuid4().hex[:8].upper()}"
        data = {
            "schedule_id": schedule_id,
            "sku": sku,
            "branch_id": branch_id,
            "new_price": new_price,
            "apply_date": apply_datetime,
            "status": "PENDING", # PENDING, APPLIED, CANCELED
            "created_at": datetime.now(),
            "created_by": created_by
        }
        self.schedules_col.document(schedule_id).set(data)
        return True, schedule_id

    def get_pending_schedules_for_product(self, sku: str, branch_id: str):
        """Lấy các lịch trình đang chờ áp dụng cho một sản phẩm cụ thể."""
        query = self.schedules_col \
            .where('sku', '==', sku) \
            .where('branch_id', '==', branch_id) \
            .where('status', '==', 'PENDING') \
            .order_by('apply_date')
        return [doc.to_dict() for doc in query.stream()]

    def cancel_schedule(self, schedule_id: str):
        """Hủy một lịch trình đã được tạo."""
        doc_ref = self.schedules_col.document(schedule_id)
        if doc_ref.get().exists:
            doc_ref.update({"status": "CANCELED"})
            return True
        return False

    def apply_pending_schedules(self):
        """
        Job chạy để áp dụng các lịch trình giá đã đến hạn.
        Đây là chức năng quan trọng cần được gọi định kỳ.
        """
        now = datetime.now()
        query = self.schedules_col \
            .where('status', '==', 'PENDING') \
            .where('apply_date', '<=', now)
        
        applied_count = 0
        for doc in query.stream():
            schedule = doc.to_dict()
            try:
                # Áp dụng giá mới vào collection chính
                self.set_price(schedule['sku'], schedule['branch_id'], schedule['new_price'])
                
                # Cập nhật trạng thái lịch trình
                doc.reference.update({"status": "APPLIED"})
                applied_count += 1
            except Exception as e:
                # Ghi log lỗi nếu cần thiết
                print(f"Error applying schedule {schedule['schedule_id']}: {e}")
        
        return applied_count
