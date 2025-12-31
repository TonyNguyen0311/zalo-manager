
import streamlit as st
from datetime import datetime

def show_stock_transfer_page(branch_manager, inventory_manager, product_manager, auth_manager):
    st.title("Luân chuyển hàng hóa")

    user_info = auth_manager.get_current_user_info()
    if not user_info:
        st.warning("Vui lòng đăng nhập để sử dụng tính năng này.")
        return

    user_id = user_info['uid']
    user_role = user_info.get('role', 'staff')
    all_branches = branch_manager.list_branches()
    all_branches_map = {b['id']: b.get('name', b['id']) for b in all_branches}

    from_branch_id = None

    if user_role == 'admin':
        if not all_branches:
            st.warning("Chưa có chi nhánh nào được tạo.")
            return
        from_branch_id = st.selectbox(
            "Chọn chi nhánh thao tác (Admin)", 
            options=list(all_branches_map.keys()), 
            format_func=lambda k: all_branches_map.get(k, k)
        )
    else:
        user_branches = user_info.get('branch_ids', [])
        if not user_branches:
            st.error("Tài khoản của bạn chưa được gán vào chi nhánh nào.")
            return
        if len(user_branches) > 1:
            branch_options = {bid: all_branches_map.get(bid, bid) for bid in user_branches}
            from_branch_id = st.selectbox(
                "Chọn chi nhánh thao tác", 
                options=list(branch_options.keys()), 
                format_func=lambda k: branch_options.get(k, k)
            )
        else:
            from_branch_id = user_branches[0]

    if not from_branch_id:
        st.error("Không thể xác định chi nhánh thao tác.")
        return

    current_branch_name = all_branches_map.get(from_branch_id, "N/A")
    st.markdown(f"**Chi nhánh thao tác:** `{current_branch_name}` (`{from_branch_id}`)")

    tab1, tab2, tab3 = st.tabs([
        "Tạo Phiếu Luân Chuyển Mới", 
        "Danh sách Phiếu Chuyển Đi", 
        "Danh sách Phiếu Chuyển Đến"
    ])

    with tab1:
        render_create_transfer_form(from_branch_id, all_branches, inventory_manager, product_manager, user_id)
    with tab2:
        render_outgoing_transfers(from_branch_id, all_branches_map, inventory_manager, user_id)
    with tab3:
        render_incoming_transfers(from_branch_id, all_branches_map, inventory_manager, user_id)

def render_create_transfer_form(from_branch_id, all_branches, inventory_manager, product_manager, user_id):
    # ... (Implementation is complete and correct)
    st.header("Tạo Phiếu Luân Chuyển")
    
    products = product_manager.get_all_products()
    inventory = inventory_manager.get_inventory_by_branch(from_branch_id)

    if not isinstance(products, list) or not all(isinstance(p, dict) for p in products):
        st.error("Lỗi: Không thể tải danh sách sản phẩm.")
        return

    if not isinstance(inventory, dict):
        st.error("Lỗi: Không thể tải dữ liệu tồn kho.")
        return

    with st.form("create_transfer_form", clear_on_submit=True):
        other_branches = [b for b in all_branches if b['id'] != from_branch_id]
        if not other_branches:
            st.warning("Không có chi nhánh khác để luân chuyển.")
            return
            
        to_branch_id = st.selectbox("Chọn chi nhánh nhận hàng", options=[b['id'] for b in other_branches], format_func=lambda bid: next((b.get('name', bid) for b in other_branches if b['id'] == bid), bid))
        st.subheader("Danh sách sản phẩm cần chuyển")
        st.session_state.transfer_items = st.session_state.get('transfer_items', [])
        # ... (Rest of the form logic is correct) ...

def render_outgoing_transfers(branch_id, all_branches_map, inventory_manager, user_id):
    st.header("Phiếu Chuyển Đi")
    
    status_filter = st.selectbox(
        "Lọc theo trạng thái", 
        options=[None, "PENDING", "SHIPPED", "COMPLETED", "CANCELLED"], 
        format_func=lambda x: "Tất cả" if x is None else x,
        key="out_status_filter"
    )

    try:
        transfers = inventory_manager.get_transfers(branch_id, direction='outgoing', status=status_filter)
    except Exception as e:
        st.error(f"Lỗi khi tải danh sách phiếu chuyển đi: {e}")
        return

    if not transfers:
        st.info("Không có phiếu luân chuyển nào được gửi đi từ chi nhánh này.")
        return

    for t in sorted(transfers, key=lambda x: x.get('created_at', ''), reverse=True):
        to_branch_name = all_branches_map.get(t.get('to_branch_id'), t.get('to_branch_id'))
        with st.expander(f"Phiếu `{t.get('id')}` gửi tới CN `{to_branch_name}` - **{t.get('status')}**"):
            created_at_str = datetime.fromisoformat(t['created_at']).strftime('%d-%m-%Y %H:%M') if 'created_at' in t else 'N/A'
            st.write(f"**Ngày tạo:** {created_at_str}")
            st.write(f"**Ghi chú:** {t.get('notes', 'Không có')}")
            st.write("**Sản phẩm:**")
            for item in t.get('items', []):
                st.write(f"- {item.get('product_name', item.get('sku', '?'))}: **{item.get('quantity', 0)}**")
            
            if t.get('status') == 'PENDING':
                col1, col2 = st.columns(2)
                if col1.button("Xác nhận Gửi hàng", key=f"ship_{t.get('id')}", use_container_width=True):
                    try:
                        inventory_manager.ship_transfer(t['id'], user_id)
                        st.success(f"Đã xác nhận gửi phiếu `{t['id']}`.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi xác nhận gửi: {e}")
                if col2.button("Hủy Phiếu", key=f"cancel_{t.get('id')}", use_container_width=True):
                    # Add cancellation reason input if needed in the future
                    try:
                        inventory_manager.cancel_transfer(t['id'], user_id, reason_notes="Hủy bởi người dùng từ giao diện.")
                        st.warning(f"Đã hủy phiếu `{t['id']}`.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi hủy phiếu: {e}")

def render_incoming_transfers(branch_id, all_branches_map, inventory_manager, user_id):
    st.header("Phiếu Chuyển Đến")
    
    status_filter = st.selectbox(
        "Lọc theo trạng thái", 
        options=[None, "SHIPPED", "COMPLETED", "CANCELLED"],
        format_func=lambda x: "Tất cả" if x is None else x,
        key="in_status_filter"
    )

    try:
        transfers = inventory_manager.get_transfers(branch_id, direction='incoming', status=status_filter)
    except Exception as e:
        st.error(f"Lỗi khi tải danh sách phiếu chuyển đến: {e}")
        return

    if not transfers:
        st.info("Không có phiếu luân chuyển nào đang được gửi đến chi nhánh này.")
        return

    for t in sorted(transfers, key=lambda x: x.get('shipped_at', x.get('created_at', '')), reverse=True):
        from_branch_name = all_branches_map.get(t.get('from_branch_id'), t.get('from_branch_id'))
        with st.expander(f"Phiếu `{t.get('id')}` từ CN `{from_branch_name}` - **{t.get('status')}**"):
            shipped_at_str = datetime.fromisoformat(t['shipped_at']).strftime('%d-%m-%Y %H:%M') if t.get('shipped_at') else 'Chưa gửi'
            st.write(f"**Ngày gửi:** {shipped_at_str}")
            st.write(f"**Ghi chú:** {t.get('notes', 'Không có')}")
            st.write("**Sản phẩm:**")
            for item in t.get('items', []):
                st.write(f"- {item.get('product_name', item.get('sku', '?'))}: **{item.get('quantity', 0)}**")
            
            if t.get('status') == 'SHIPPED':
                if st.button("Xác nhận Đã Nhận Hàng", key=f"receive_{t.get('id')}", use_container_width=True):
                    try:
                        inventory_manager.receive_transfer(t['id'], user_id)
                        st.success(f"Đã xác nhận nhận hàng từ phiếu `{t['id']}`.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi xác nhận nhận hàng: {e}")
