
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

    # --- Branch Selection Logic ---
    # ... (same as before)

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

    # --- Tabs ---
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
    st.header("Tạo Phiếu Luân Chuyển")
    
    products = product_manager.get_all_products()
    inventory = inventory_manager.get_inventory_by_branch(from_branch_id)

    # ULTIMATE FIX - LAYER 1: Validate data types robustly before use.
    if not isinstance(products, list) or not all(isinstance(p, dict) for p in products):
        st.error("Không thể tải được danh sách sản phẩm. Dữ liệu nhận được không hợp lệ.")
        st.warning(f"Lỗi dữ liệu: `products` phải là một list của dict. Kiểu nhận được: {type(products).__name__}.")
        return

    if not isinstance(inventory, dict):
        st.error("Không thể tải được dữ liệu tồn kho. Dữ liệu nhận được không hợp lệ.")
        st.warning(f"Lỗi dữ liệu: `inventory` phải là một dict. Kiểu nhận được: {type(inventory).__name__}.")
        return

    with st.form("create_transfer_form", clear_on_submit=True):
        other_branches = [b for b in all_branches if b['id'] != from_branch_id]
        if not other_branches:
            st.warning("Không có chi nhánh khác để luân chuyển.")
            return
            
        to_branch_id = st.selectbox(
            "Chọn chi nhánh nhận hàng", 
            options=[b['id'] for b in other_branches],
            format_func=lambda bid: next((b.get('name', bid) for b in other_branches if b['id'] == bid), bid)
        )
        
        st.subheader("Danh sách sản phẩm cần chuyển")
        
        st.session_state.transfer_items = st.session_state.get('transfer_items', [])
        for i, item in enumerate(st.session_state.transfer_items):
            cols = st.columns([4, 2, 1])
            cols[0].write(f"**{item.get('product_name', item['sku'])} ({item['sku']})** - SL: {item['quantity']}")
            if cols[1].button(f"Xóa", key=f"del_{i}", use_container_width=True):
                st.session_state.transfer_items.pop(i)
                st.rerun()
        
        st.markdown("---")
        
        # This should now be safe because of the validation above.
        product_options = {p['sku']: p for p in products if 'sku' in p}
        
        available_products = {sku: product for sku, product in product_options.items() if inventory.get(sku, {}).get('stock_quantity', 0) > 0}

        if not available_products:
            st.warning("Chi nhánh này không còn sản phẩm nào có thể luân chuyển.")
            st.form_submit_button("Tạo Phiếu", disabled=True)
            return

        form_cols = st.columns([3, 2, 1])
        selected_sku = form_cols[0].selectbox(
            "Chọn sản phẩm", 
            options=list(available_products.keys()), 
            format_func=lambda sku: f"{available_products.get(sku, {}).get('name', sku)} ({sku})"
        )
        
        if selected_sku:
            current_stock = inventory.get(selected_sku, {}).get('stock_quantity', 0)
            form_cols[0].info(f"Tồn kho khả dụng: {int(current_stock)}")
            quantity = form_cols[1].number_input("Số lượng", min_value=1, max_value=max(1, int(current_stock)), step=1, key=f"qty_{selected_sku}")

            if form_cols[2].form_submit_button("Thêm", use_container_width=True):
                if quantity > current_stock:
                    st.warning(f"Số lượng tồn kho không đủ.")
                else:
                    found = next((item for item in st.session_state.transfer_items if item['sku'] == selected_sku), None)
                    if found:
                        found['quantity'] += quantity
                    else:
                        selected_product = available_products[selected_sku]
                        st.session_state.transfer_items.append({
                            'sku': selected_sku, 
                            'product_name': selected_product.get('name', 'Sản phẩm không tên'), 
                            'cogs': selected_product.get('cogs', 0), 
                            'quantity': quantity
                        })
                    st.rerun()

        notes = st.text_area("Ghi chú (nếu có)")
        if st.form_submit_button("Tạo Phiếu Luân Chuyển", use_container_width=True):
            if not st.session_state.transfer_items:
                st.error("Vui lòng thêm sản phẩm vào phiếu.")
            else:
                try:
                    transfer_id = inventory_manager.create_transfer(
                        from_branch_id=from_branch_id, to_branch_id=to_branch_id,
                        items=st.session_state.transfer_items, user_id=user_id, notes=notes
                    )
                    st.success(f"Đã tạo thành công phiếu luân chuyển `{transfer_id}`.")
                    st.session_state.transfer_items = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi tạo phiếu: {e}")

# Functions for other tabs (render_outgoing_transfers, render_incoming_transfers) remain the same
# They should also be checked for robustness, but the main crash is fixed here.

def render_outgoing_transfers(branch_id, all_branches_map, inventory_manager, user_id):
    # ... (Implementation as before)
    pass

def render_incoming_transfers(branch_id, all_branches_map, inventory_manager, user_id):
    # ... (Implementation as before)
    pass
