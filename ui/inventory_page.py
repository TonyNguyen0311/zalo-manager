
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Import managers
from managers.inventory_manager import InventoryManager
from managers.product_manager import ProductManager
from managers.branch_manager import BranchManager
from managers.auth_manager import AuthManager

def render_inventory_page(inv_mgr: InventoryManager, prod_mgr: ProductManager, branch_mgr: BranchManager, auth_mgr: AuthManager):
    st.header("Quản lý Tồn kho")

    # --- 1. LẤY THÔNG TIN & PHÂN QUYỀN ---
    user_info = auth_mgr.get_current_user_info()
    if not user_info:
        st.error("Vui lòng đăng nhập để sử dụng chức năng này.")
        return

    user_role = user_info.get('role', 'staff')
    user_branches = user_info.get('branch_ids', [])
    all_branches_map = {b['id']: b['name'] for b in branch_mgr.list_branches(active_only=False)}

    allowed_branches_map = {}
    if user_role == 'admin':
        allowed_branches_map = all_branches_map
        default_branch_selection = list(allowed_branches_map.keys())[0] if allowed_branches_map else None
    else:
        if not user_branches:
            st.warning("Tài khoản của bạn chưa được gán vào chi nhánh nào.")
            return
        allowed_branches_map = {branch_id: all_branches_map[branch_id] for branch_id in user_branches if branch_id in all_branches_map}
        default_branch_selection = user_branches[0]

    if not allowed_branches_map:
        st.warning("Không có chi nhánh nào để quản lý.")
        return

    # --- 2. BỘ LỌC CHI NHÁNH ---
    if len(allowed_branches_map) > 1:
        selected_branch = st.selectbox("Chọn chi nhánh để xem kho", options=list(allowed_branches_map.keys()), format_func=lambda x: allowed_branches_map[x], index=list(allowed_branches_map.keys()).index(default_branch_selection))
    else:
        selected_branch = default_branch_selection
        st.text_input("Chi nhánh", value=allowed_branches_map[selected_branch], disabled=True)
    st.divider()

    # --- 3. CẤU TRÚC TAB ---
    tab1, tab2, tab3 = st.tabs(["📊 Tình hình Tồn kho", "📥 Nhập hàng", "📜 Lịch sử Thay đổi"])

    # Tải dữ liệu cần thiết một lần
    branch_inventory = inv_mgr.get_inventory_by_branch(selected_branch)
    all_products = prod_mgr.list_products() # Lấy tất cả sản phẩm để map thông tin
    product_map = {p['sku']: p for p in all_products if 'sku' in p}

    # =========================================================
    # TAB 1: TÌNH HÌNH TỒN KHO
    # =========================================================
    with tab1:
        st.subheader(f"Tồn kho hiện tại của: {allowed_branches_map[selected_branch]}")

        if not branch_inventory:
            st.info("Chưa có sản phẩm nào trong kho của chi nhánh này.")
        else:
            inventory_list = []
            for sku, inv_data in branch_inventory.items():
                prod_info = product_map.get(sku, {})
                quantity = inv_data.get('stock_quantity', 0)
                threshold = inv_data.get('low_stock_threshold', 10)
                status = "Hết hàng" if quantity <= 0 else ("Sắp hết" if quantity < threshold else "Còn hàng")

                inventory_list.append({
                    'Tên sản phẩm': prod_info.get('name', f'Không rõ (SKU: {sku})'),
                    'SKU': sku,
                    'Số lượng': quantity,
                    'Trạng thái': status
                })
            
            inventory_df = pd.DataFrame(inventory_list)

            # Highlight các dòng sắp hết hoặc hết hàng
            def highlight_status(row):
                if row['Trạng thái'] == 'Hết hàng':
                    return ['background-color: #FFC7CE'] * len(row)
                elif row['Trạng thái'] == 'Sắp hết':
                    return ['background-color: #FFEB9C'] * len(row)
                return [''] * len(row)

            st.dataframe(inventory_df.style.apply(highlight_status, axis=1), use_container_width=True, hide_index=True)

    # =========================================================
    # TAB 2: NHẬP HÀNG
    # =========================================================
    with tab2:
        st.subheader("Tạo Phiếu Nhập hàng")
        
        # Form nhập hàng
        with st.form("receive_stock_form", clear_on_submit=True):
            product_options = {p['sku']: f"{p['name']} ({p['sku']})" for p in all_products if 'sku' in p}
            selected_sku = st.selectbox("Chọn sản phẩm", options=list(product_options.keys()), format_func=lambda x: product_options[x])
            
            c1, c2 = st.columns(2)
            with c1:
                quantity = st.number_input("Số lượng nhập", min_value=1, step=1)
            with c2:
                cost_price = st.number_input("Giá nhập (trên 1 đơn vị)", min_value=0, step=1000)

            supplier = st.text_input("Nhà cung cấp (tùy chọn)")
            notes = st.text_area("Ghi chú (tùy chọn)")

            submitted = st.form_submit_button("Xác nhận Nhập hàng", type="primary")

        if submitted:
            if not selected_sku:
                st.warning("Vui lòng chọn một sản phẩm.")
            else:
                try:
                    with st.spinner("Đang xử lý..."):
                        inv_mgr.receive_stock(
                            sku=selected_sku,
                            branch_id=selected_branch,
                            quantity=quantity,
                            user_id=user_info['uid'],
                            cost_price=cost_price,
                            supplier=supplier,
                            notes=notes
                        )
                    st.success(f"Nhập hàng thành công cho sản phẩm {product_options[selected_sku]}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Đã xảy ra lỗi: {e}")

    # =========================================================
    # TAB 3: LỊCH SỬ THAY ĐỔI
    # =========================================================
    with tab3:
        st.subheader("Lịch sử Nhập/Xuất/Điều chỉnh Kho")
        with st.spinner("Đang tải lịch sử..."):
            history = inv_mgr.get_inventory_adjustments_history(branch_id=selected_branch, limit=100)

        if not history:
            st.info("Chưa có lịch sử thay đổi nào cho chi nhánh này.")
        else:
            history_df = pd.DataFrame(history)
            # Xử lý để hiển thị thông tin dễ đọc hơn
            history_df['Sản phẩm'] = history_df['sku'].map(lambda s: product_map.get(s, {}).get('name', s))
            history_df['Thời gian'] = pd.to_datetime(history_df['timestamp']).dt.strftime('%d/%m/%Y %H:%M')
            history_df.rename(columns={
                'delta': 'Thay đổi',
                'quantity_before': 'Tồn trước',
                'quantity_after': 'Tồn sau',
                'reason': 'Lý do',
                'notes': 'Ghi chú'
            }, inplace=True)
            st.dataframe(history_df[['Thời gian', 'Sản phẩm', 'Thay đổi', 'Tồn trước', 'Tồn sau', 'Lý do', 'Ghi chú']], use_container_width=True, hide_index=True)
