
import streamlit as st
from datetime import datetime, time

def render_pricing_page():
    st.header("⚙️ Thiết lập Giá bán")

    # 1. LẤY MANAGERS
    product_mgr = st.session_state.product_mgr
    branch_mgr = st.session_state.branch_mgr
    price_mgr = st.session_state.price_mgr
    current_user = st.session_state.user

    # 2. KHỞI TẠO STATE
    if 'pricing_selected_sku' not in st.session_state:
        st.session_state.pricing_selected_sku = None
    if 'pricing_selected_branch' not in st.session_state:
        # Mặc định là chi nhánh của user, nếu là ADMIN thì có thể đổi
        st.session_state.pricing_selected_branch = current_user['branch_id']

    # 3. LẤY DỮ LIỆU GỐC
    master_products = product_mgr.list_products()
    categories = product_mgr.get_categories()
    suppliers = [] # TODO: product_mgr.get_suppliers() is not implemented yet.
    branches = branch_mgr.list_branches()

    # 4. BỐ CỤC 2 CỘT
    col_left, col_right = st.columns([1, 1])

    # =============================================
    # CỘT TRÁI - DANH SÁCH SẢN PHẨM & BỘ LỌC
    # =============================================
    with col_left:
        st.subheader("Danh sách sản phẩm")
        
        # --- BỘ LỌC --
        search_query = st.text_input("🔍 Tìm theo Tên hoặc SKU")
        
        # Lọc theo danh mục
        cat_options = {cat['id']: cat['name'] for cat in categories}
        cat_options['ALL'] = "Tất cả danh mục"
        selected_cat = st.selectbox(
            "Lọc theo danh mục", 
            options=['ALL'] + list(cat_options.keys()),
            format_func=lambda x: cat_options.get(x, "Tất cả")
        )

        # Lọc theo NCC (Tạm thời vô hiệu hóa)
        sup_options = {sup['id']: sup['name'] for sup in suppliers}
        sup_options['ALL'] = "Tất cả nhà cung cấp"
        selected_sup = st.selectbox(
            "Lọc theo nhà cung cấp", 
            options=['ALL'] + list(sup_options.keys()),
            format_func=lambda x: sup_options.get(x, "Tất cả"),
            disabled=not suppliers # Vô hiệu hóa nếu không có NCC
        )
        
        st.divider()

        # --- HIỂN THỊ DANH SÁCH --
        filtered_list = master_products
        if search_query:
            search_query = search_query.lower()
            filtered_list = [p for p in filtered_list if search_query in p['name'].lower() or search_query in p['sku'].lower()]
        if selected_cat != 'ALL':
            filtered_list = [p for p in filtered_list if p.get('category_id') == selected_cat]
        if selected_sup != 'ALL':
            filtered_list = [p for p in filtered_list if p.get('supplier_id') == selected_sup]

        # Bảng hiển thị sản phẩm
        for p in filtered_list:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                col1.markdown(f"**{p['name']}**<br><small>{p['sku']}</small>", unsafe_allow_html=True)
                if col2.button("Chọn", key=f"select_{p['sku']}", use_container_width=True):
                    st.session_state.pricing_selected_sku = p['sku']
                    st.rerun() # Chạy lại để cột phải cập nhật

    # =============================================
    # CỘT PHẢI - CHI TIẾT & CÀI ĐẶT GIÁ
    # =============================================
    with col_right:
        st.subheader("Chi tiết & Cài đặt giá")
        
        if not st.session_state.pricing_selected_sku:
            st.info("Chọn một sản phẩm từ danh sách bên trái để bắt đầu.")
        else:
            sku = st.session_state.pricing_selected_sku
            # Tìm thông tin sản phẩm từ list đã có
            product_info = next((p for p in master_products if p['sku'] == sku), None)
            
            if not product_info:
                st.error(f"Không tìm thấy thông tin sản phẩm cho SKU: {sku}")
                st.stop()

            st.markdown(f"#### **{product_info['name']}** ({sku})")

            # --- Chọn chi nhánh ---
            branch_options = {b['id']: b['name'] for b in branches}
            # Chỉ admin mới được chọn các chi nhánh khác
            is_admin = (current_user['role'] == 'ADMIN')
            
            selected_branch_id = st.selectbox(
                "Chọn chi nhánh để cài đặt giá",
                options=list(branch_options.keys()),
                format_func=lambda x: branch_options[x],
                key='pricing_selected_branch',
                disabled=not is_admin
            )
            
            st.divider()

            # --- Form cài đặt giá mới ---
            st.markdown("##### Cài đặt giá mới")

            # Lấy giá hiện tại và giá cũ
            current_price = price_mgr.get_current_price_for_sku(selected_branch_id, sku)
            price_history = price_mgr.get_price_history_for_sku(selected_branch_id, sku)
            old_price = price_history[1]['new_price'] if len(price_history) > 1 else 0

            col_price1, col_price2 = st.columns(2)
            col_price1.metric("Giá hiện tại", f"{current_price:,.0f} đ")
            col_price2.metric("Giá cũ", f"{old_price:,.0f} đ")


            new_price = st.number_input("Giá bán mới (VNĐ)", min_value=0, step=1000)
            
            d_col1, d_col2 = st.columns(2)
            start_date_input = d_col1.date_input("Ngày bắt đầu hiệu lực", value=datetime.now())
            end_date_input = d_col2.date_input("Ngày kết thúc (bỏ trống nếu vô hạn)", value=None)

            # Chuyển đổi date thành datetime
            start_datetime = datetime.combine(start_date_input, time.min)
            end_datetime = datetime.combine(end_date_input, time.max) if end_date_input else None

            if st.button("Lưu Lịch trình giá", type="primary", use_container_width=True):
                success, msg = price_mgr.create_price_schedule(
                    branch_id=selected_branch_id,
                    sku=sku,
                    new_price=float(new_price),
                    start_date=start_datetime,
                    end_date=end_datetime,
                    created_by=current_user['id']
                )
                if success:
                    st.success(f"Đã lên lịch thay đổi giá cho {sku} thành công!")
                    # Có thể thêm logic để refresh lại bảng lịch sử bên dưới
                else:
                    st.error(f"Lỗi: {msg}")

            st.divider()

            # --- Hiển thị lịch sử giá ---
            st.markdown("##### Lịch sử thay đổi giá")
            schedules = price_mgr.get_price_schedules_for_sku(selected_branch_id, sku) # Lấy cả schedule
            if not schedules:
                st.write("Chưa có lịch sử/lịch trình giá cho sản phẩm này tại chi nhánh đã chọn.")
            else:
                for item in schedules:
                    start = item['start_date'].strftime('%d-%m-%Y')
                    end = item.get('end_date')
                    end_str = end.strftime('%d-%m-%Y') if end else "Vô hạn"
                    price_str = f"{item['new_price']:,.0f} đ"
                    st.info(f"**{price_str}** | Từ: {start} | Đến: {end_str} | **{item['status']}**")
