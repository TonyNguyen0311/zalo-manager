
from google.cloud import firestore
from google.cloud.firestore import Query
from datetime import datetime
import uuid

class PriceManager:
    def __init__(self, firebase_client):
        self.db = firebase_client.db
        self.schedules_col = self.db.collection('price_schedules')

    def create_price_schedule(self, branch_id, sku, new_price, start_date, end_date=None, created_by=None):
        """
        Tạo một lịch trình áp dụng giá mới.

        Args:
            branch_id (str): ID của chi nhánh.
            sku (str): Mã sản phẩm.
            new_price (float): Giá bán mới.
            start_date (datetime): Ngày bắt đầu hiệu lực.
            end_date (datetime, optional): Ngày kết thúc hiệu lực. Defaults to None.
            created_by (str, optional): User ID của người tạo. Defaults to None.

        Returns:
            tuple: (bool, str) - (Thành công, ID lịch trình hoặc thông báo lỗi).
        """
        if not all([branch_id, sku, isinstance(new_price, (int, float)), start_date]):
            return False, "Dữ liệu đầu vào không hợp lệ."
        
        schedule_id = f"SCH-{uuid.uuid4().hex[:8].upper()}"
        
        data = {
            "schedule_id": schedule_id,
            "branch_id": branch_id,
            "sku": sku,
            "new_price": new_price,
            "start_date": start_date,
            "end_date": end_date,
            "status": "PENDING", # Sẽ có một quy trình để kích hoạt nó sau
            "created_at": datetime.now(),
            "created_by": created_by
        }
        
        # Logic để kiểm tra chồng chéo lịch trình có thể được thêm vào đây

        self.schedules_col.document(schedule_id).set(data)
        return True, schedule_id

    def get_current_price_for_sku(self, branch_id, sku, on_date=None):
        """
        Lấy giá bán đang có hiệu lực của sản phẩm tại một chi nhánh vào một ngày cụ thể.
        Nếu không có giá được thiết lập, trả về 0.
        
        Args:
            branch_id (str): ID chi nhánh.
            sku (str): Mã sản phẩm.
            on_date (datetime, optional): Ngày cần kiểm tra. Mặc định là bây giờ.

        Returns:
            float: Giá bán hiện tại, hoặc 0 nếu không tìm thấy.
        """
        check_date = on_date or datetime.now()

        # Tìm lịch trình có ngày bắt đầu gần nhất trong quá khứ
        query = self.schedules_col \
            .where('branch_id', '==', branch_id) \
            .where('sku', '==', sku) \
            .where('start_date', '<=', check_date) \
            .order_by('start_date', direction=Query.DESCENDING) \
            .limit(1)
        
        docs = list(query.stream())
        
        if not docs:
            return 0 # Không có lịch trình nào bắt đầu trong quá khứ

        latest_schedule = docs[0].to_dict()

        # Kiểm tra xem lịch trình có bị hết hạn không
        if latest_schedule.get('end_date') and latest_schedule['end_date'] < check_date:
            return 0 # Lịch trình gần nhất đã hết hạn

        return latest_schedule.get('new_price', 0)

    def get_price_history_for_sku(self, branch_id, sku):
        """
        Lấy lịch sử giá của một sản phẩm tại một chi nhánh.
        """
        query = self.schedules_col \
            .where('branch_id', '==', branch_id) \
            .where('sku', '==', sku) \
            .order_by('start_date', direction=Query.DESCENDING)
        
        history = [doc.to_dict() for doc in query.stream()]
        return history

    def run_price_activation_job(self):
        """
        Một công việc (job) chạy nền định kỳ để cập nhật trạng thái các lịch trình giá.
        PENDING -> ACTIVE nếu đến ngày.
        ACTIVE -> EXPIRED nếu hết hạn.
        """
        now = datetime.now()
        
        # Kích hoạt các lịch trình PENDING
        pending_query = self.schedules_col.where('status', '==', 'PENDING').where('start_date', '<=', now)
        for doc in pending_query.stream():
            schedule = doc.to_dict()
            # Kiểm tra xem có bị hết hạn luôn không
            if schedule.get('end_date') and schedule['end_date'] < now:
                doc.reference.update({'status': 'EXPIRED'})
            else:
                doc.reference.update({'status': 'ACTIVE'})
        
        # Hủy kích hoạt các lịch trình ACTIVE
        active_query = self.schedules_col.where('status', '==', 'ACTIVE').where('end_date', '<=', now)
        for doc in active_query.stream():
            doc.reference.update({'status': 'EXPIRED'})

        return True, "Price activation job completed."
