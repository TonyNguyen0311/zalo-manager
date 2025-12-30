
import uuid
from google.cloud import firestore
from datetime import datetime

class InventoryManager:
    def __init__(self, firebase_client):
        self.db = firebase_client.db
        # --- Collections ---
        self.inventory_col = self.db.collection('inventory')
        self.transfers_col = self.db.collection('goods_transfers')
        self.adjustments_col = self.db.collection('stock_adjustments')
        self.stock_takes_col = self.db.collection('stock_takes')


    def _get_doc_id(self, sku: str, branch_id: str):
        return f"{sku.upper()}_{branch_id}"

    # --------------------------------------------------------------------------
    # SECTION 1: GOODS TRANSFER (LUÂN CHUYỂN KHO - LOGIC MỚI)
    # --------------------------------------------------------------------------

    @firestore.transactional
    def create_stock_transfer_transaction(self, transaction, from_branch_id, to_branch_id, items, user_id, notes):
        transfer_id = f"TFR-{uuid.uuid4().hex[:8].upper()}"
        transfer_ref = self.transfers_col.document(transfer_id)

        # 1. Tạo phiếu chuyển kho với trạng thái PENDING
        transfer_data = {
            "id": transfer_id,
            "branch_from_id": from_branch_id,
            "branch_to_id": to_branch_id,
            "items": items, # list of {'SKU': str, 'Số lượng': int}
            "status": "PENDING", # PENDING -> COMPLETED
            "created_by": user_id,
            "created_at": datetime.now().isoformat(),
            "notes": notes
        }
        transaction.set(transfer_ref, transfer_data)

        # 2. Cập nhật tồn kho ở chi nhánh GỬI
        for item in items:
            sku = item['SKU']
            quantity = item['Số lượng']
            inv_doc_ref = self.inventory_col.document(self._get_doc_id(sku, from_branch_id))
            
            # Giảm tồn kho thực tế, tăng tồn kho "đang chuyển đi"
            transaction.set(inv_doc_ref, {
                'stock_quantity': firestore.FieldValue.increment(-quantity),
                'outgoing_quantity': firestore.FieldValue.increment(quantity),
                'last_updated': datetime.now().isoformat(),
                'sku': sku, 
                'branch_id': from_branch_id
            }, merge=True)

    def create_stock_transfer(self, from_branch_id, to_branch_id, items, user_id, notes):
        # Hàm wrapper để gọi transaction
        transaction = self.db.transaction()
        self.create_stock_transfer_transaction(transaction, from_branch_id, to_branch_id, items, user_id, notes)

    @firestore.transactional
    def confirm_stock_transfer_transaction(self, transaction, transfer_id, user_id):
        transfer_ref = self.transfers_col.document(transfer_id)
        transfer_snapshot = transfer_ref.get(transaction=transaction).to_dict()

        if transfer_snapshot['status'] != 'PENDING':
            raise Exception("Phiếu này không ở trạng thái chờ xác nhận.")

        # 1. Cập nhật trạng thái phiếu thành COMPLETED
        transaction.update(transfer_ref, {
            "status": "COMPLETED",
            "received_by": user_id,
            "received_at": datetime.now().isoformat()
        })

        branch_from_id = transfer_snapshot['branch_from_id']
        branch_to_id = transfer_snapshot['branch_to_id']
        items = transfer_snapshot['items']

        # 2. Cập nhật tồn kho ở cả 2 chi nhánh
        for item in items:
            sku = item['SKU']
            quantity = item['Số lượng']

            # 2a. Chi nhánh GỬI: giảm số lượng "đang chuyển đi"
            from_inv_ref = self.inventory_col.document(self._get_doc_id(sku, branch_from_id))
            transaction.update(from_inv_ref, {
                'outgoing_quantity': firestore.FieldValue.increment(-quantity),
                'last_updated': datetime.now().isoformat()
            })

            # 2b. Chi nhánh NHẬN: tăng tồn kho thực tế
            to_inv_ref = self.inventory_col.document(self._get_doc_id(sku, branch_to_id))
            transaction.set(to_inv_ref, {
                'stock_quantity': firestore.FieldValue.increment(quantity),
                'last_updated': datetime.now().isoformat(),
                'sku': sku,
                'branch_id': branch_to_id
            }, merge=True)

    def confirm_stock_transfer(self, transfer_id, user_id):
        # Hàm wrapper để gọi transaction
        transaction = self.db.transaction()
        self.confirm_stock_transfer_transaction(transaction, transfer_id, user_id)

    def get_pending_transfers_to_branches(self, branch_ids: list):
        """Lấy các phiếu đang ở trạng thái PENDING và đi đến các chi nhánh được chỉ định."""
        if not branch_ids:
            return []
        query = self.transfers_col.where("status", "==", "PENDING").where("branch_to_id", "in", branch_ids)
        return [doc.to_dict() for doc in query.order_by("created_at", direction=firestore.Query.DESCENDING).stream()]


    # --------------------------------------------------------------------------
    # SECTION 2: CÁC HÀM KHÁC (giữ nguyên để tham khảo)
    # --------------------------------------------------------------------------
    def get_stock(self, sku: str, branch_id: str):
        doc_id = self._get_doc_id(sku, branch_id)
        doc = self.inventory_col.document(doc_id).get()
        if doc.exists:
            return doc.to_dict().get('stock_quantity', 0)
        return 0

    def get_inventory_by_branch(self, branch_id: str):
        docs = self.inventory_col.where('branch_id', '==', branch_id).stream()
        return {doc.to_dict()['sku']: doc.to_dict() for doc in docs}
