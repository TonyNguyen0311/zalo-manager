"""
Module này chịu trách nhiệm xử lý tất cả logic liên quan đến chi phí sản phẩm,
bao gồm tính giá vốn bình quân gia quyền và cung cấp dữ liệu chi phí cho báo cáo.
"""

from .firebase_client import db
from google.cloud.firestore import server_timestamp

class CostManager:
    def __init__(self):
        """
        Khởi tạo CostManager với một kết nối đến Firestore.
        """
        self.db = db

    def record_shipment_and_update_avg_cost(self, product_id, branch_id, quantity, unit_cost):
        """
        Ghi nhận một lô hàng mới và tính toán lại giá vốn bình quân gia quyền
        cho sản phẩm tại một chi nhánh cụ thể.

        Args:
            product_id (str): ID của sản phẩm.
            branch_id (str): ID của chi nhánh nhận hàng.
            quantity (int): Số lượng nhập.
            unit_cost (float): Giá vốn trên mỗi đơn vị của lô hàng này.

        Returns:
            float: Giá vốn bình quân mới.
        """
        # Sử dụng một transaction để đảm bảo tính toàn vẹn dữ liệu
        transaction = self.db.transaction()
        inventory_ref = self.db.collection('branch_inventory').document(f"{branch_id}_{product_id}")

        @firestore.transactional
        def update_in_transaction(transaction, inventory_ref):
            # 1. Lấy thông tin tồn kho hiện tại của sản phẩm tại chi nhánh
            inventory_snapshot = inventory_ref.get(transaction=transaction)
            
            current_quantity = 0
            current_avg_cost = 0.0

            if inventory_snapshot.exists:
                inventory_data = inventory_snapshot.to_dict()
                current_quantity = inventory_data.get('quantity', 0)
                current_avg_cost = inventory_data.get('average_cost', 0.0)

            # 2. Tính toán giá vốn bình quân mới
            total_cost = (current_quantity * current_avg_cost) + (quantity * unit_cost)
            new_quantity = current_quantity + quantity
            new_avg_cost = total_cost / new_quantity if new_quantity > 0 else 0

            # 3. Cập nhật tồn kho với số lượng và giá vốn mới
            transaction.set(inventory_ref, {
                'product_id': product_id,
                'branch_id': branch_id,
                'quantity': new_quantity,
                'average_cost': new_avg_cost,
                'last_updated': server_timestamp()
            }, merge=True)

            # 4. Ghi log lại nghiệp vụ nhập hàng để kiểm toán
            log_ref = self.db.collection('shipment_logs').document()
            transaction.set(log_ref, {
                'product_id': product_id,
                'branch_id': branch_id,
                'quantity': quantity,
                'unit_cost': unit_cost,
                'new_average_cost': new_avg_cost,
                'timestamp': server_timestamp()
            })
            
            return new_avg_cost

        return update_in_transaction(transaction, inventory_ref)

    def get_cogs_for_items(self, branch_id, items):
        """
        Lấy tổng Giá vốn hàng bán (COGS) cho một danh sách các mặt hàng đã bán.

        Args:
            branch_id (str): Chi nhánh nơi diễn ra giao dịch.
            items (list): List các dict, mỗi dict chứa 'product_id' và 'quantity'.

        Returns:
            float: Tổng giá vốn của các mặt hàng.
        """
        total_cogs = 0.0
        for item in items:
            product_id = item['product_id']
            quantity = item['quantity']

            inventory_ref = self.db.collection('branch_inventory').document(f"{branch_id}_{product_id}")
            inventory_doc = inventory_ref.get()

            if inventory_doc.exists:
                # Lấy giá vốn trung bình đã được tính toán trước đó
                avg_cost = inventory_doc.to_dict().get('average_cost', 0.0)
                total_cogs += avg_cost * quantity
        
        return total_cogs
