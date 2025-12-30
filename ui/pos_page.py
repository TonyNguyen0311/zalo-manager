import streamlit as st
import pandas as pd
from datetime import datetime

def render_pos_page():
    st.header("🛒 Bán hàng (POS)")

    # Lấy các manager và thông tin cần thiết
    product_mgr = st.session_state.product_mgr
    customer_mgr = st.session_state.customer_mgr
    inventory_mgr = st.session_state.inventory_mgr
    pos_mgr = st.session_state.pos_mgr
    promotion_mgr = st.session_state.promotion_mgr
    current_branch_id = st.session_state.user['branch_id']

    # ---- KHỞI TẠO STATE ----
    if 'cart' not in st.session_state:
        st.session_state.cart = []
    if 'manual_discount_percent' not in st.session_state:
        st.session_state.manual_discount_percent = 0
    
    # Lấy chương trình khuyến mãi đang hoạt động
    active_program = promotion_mgr.get_active_price_program()
    
    # Lấy quy tắc và phạm vi từ chương trình KM (nếu có)
    auto_discount_percent = 0
    manual_discount_limit = 0
    program_scope = {"type": "NONE", "ids": []}
    if active_program:
        auto_discount_percent = active_program.get('rules', {}).get('auto_discount', {}).get('value', 0)
        manual_discount_limit = active_program.get('rules', {}).get('manual_extra_limit', {}).get('value', 0)
        program_scope = active_program.get('scope', program_scope)

    # ---- HÀM KIỂM TRA SẢN PHẨM HỢP LỆ CHO KHUYẾN MÃI ---
    def is_item_eligible_for_promo(item, scope):
        if scope['type'] == "ALL":
            return True
        if scope['type'] == "PRODUCT" and item['sku'] in scope['ids']:
            return True
        if scope['type'] == "CATEGORY" and item['category_id'] in scope['ids']:
            return True
        return False

    # ---- TÍNH TOÁN GIỎ HÀNG ----
    subtotal = 0
    total_auto_discount = 0
    cart_items_for_order = []

    for item in st.session_state.cart:
        original_line_total = item['original_price'] * item['quantity']
        subtotal += original_line_total
        line_auto_discount = 0
        
        # Áp dụng giảm giá tự động NẾU sản phẩm hợp lệ
        if active_program and is_item_eligible_for_promo(item, program_scope):
            line_auto_discount = original_line_total * (auto_discount_percent / 100)
            total_auto_discount += line_auto_discount

        # Tạo item cho việc lưu đơn hàng
        cart_items_for_order.append({
            "sku": item["sku"],
            "name": item["name"],
            "original_price": item['original_price'],
            "quantity": item["quantity"],
            "final_price_after_discounts": (original_line_total - line_auto_discount) / item['quantity']
        })

    # Áp dụng giảm giá thủ công trên tổng đơn
    total_manual_discount = subtotal * (st.session_state.manual_discount_percent / 100)
    final_total = subtotal - total_auto_discount - total_manual_discount

    # Cập nhật lại final price trong list items để trừ nốt phần discount thủ công
    if subtotal > 0:
        for item in cart_items_for_order:
            proportional_manual_discount = (item['original_price'] * item['quantity'] / subtotal) * total_manual_discount
            item['final_price_after_discounts'] -= proportional_manual_discount / item['quantity']

    # ---- GIAO DIỆN ----
    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Thông tin đơn hàng")
        
        # Hiển thị chương trình khuyến mãi
        if active_program:
            st.success(f"🎉 Đang áp dụng: {active_program['name']}")
        else:
            st.info("Không có chương trình giá nào đang hoạt động.")

        customers = customer_mgr.list_customers()
        customer_options = {c['id']: f"{c['name']} - {c['phone']}" for c in customers}
        customer_options["-"] = "Khách vãng lai"
        selected_customer_id = st.selectbox("👤 Khách hàng", list(customer_options.keys()), format_func=lambda x: customer_options[x], index=len(customer_options) - 1)

        st.divider()
        st.subheader("Giỏ hàng")

        if not st.session_state.cart:
            st.info("Giỏ hàng đang trống")
        else:
            cart_df_display = pd.DataFrame([{"Tên SP": i['name'], "SL": i['quantity'], "Đơn giá": i['original_price']} for i in st.session_state.cart])
            st.dataframe(cart_df_display, use_container_width=True, hide_index=True)

            with st.form("payment_form"):
                st.number_input("Giảm giá thêm (%)", min_value=0.0, max_value=float(manual_discount_limit), step=1.0, key="manual_discount_percent")
                st.metric("Tổng tiền hàng", f"{subtotal:,.0f} VNĐ")
                st.metric("Giảm giá", f"- {total_auto_discount + total_manual_discount:,.0f} VNĐ")
                st.markdown("###")
                st.metric("✅ KHÁCH CẦN TRẢ", f"{final_total:,.0f} VNĐ")
                submitted_payment = st.form_submit_button("💳 THANH TOÁN", use_container_width=True, type="primary")

            if submitted_payment:
                # Build order data
                # ... (logic gửi đơn hàng tương tự như cũ)
                st.rerun()

        if st.session_state.cart and not submitted_payment:
            if st.button("🗑️ Xóa giỏ hàng", use_container_width=True):
                st.session_state.cart = []
                st.session_state.manual_discount_percent = 0
                st.rerun()

    with col2:
        st.subheader("Thêm sản phẩm")
        products = product_mgr.list_products()
        branch_inventory = inventory_mgr.get_inventory_by_branch(current_branch_id)

        product_display_list = [{
            "sku": p['sku'], 
            "name": p['name'], 
            "category_id": p.get('category_id'), # Thêm category_id
            "price": p.get('price_default', 0),
            "stock": branch_inventory.get(p['sku'], {}).get('stock_quantity', 0)
        } for p in products]
        
        product_df = pd.DataFrame([p for p in product_display_list if p['stock'] > 0])

        if product_df.empty:
            st.warning("Tất cả sản phẩm tại chi nhánh này đã hết hàng.")
            return

        options = [f"{name} | Tồn kho: {stock}" for name, stock in zip(product_df["name"], product_df["stock"])]
        selected_product_str = st.selectbox("Chọn hoặc tìm sản phẩm", options)

        if selected_product_str:
            selected_name = selected_product_str.split(' |')[0]
            selected_row = product_df[product_df['name'] == selected_name].iloc[0]
            
            col_q, col_b = st.columns([1, 2])
            quantity = col_q.number_input("Số lượng", 1, int(selected_row['stock']), 1)
            
            if col_b.button("Thêm vào giỏ", use_container_width=True):
                existing_item = next((item for item in st.session_state.cart if item["sku"] == selected_row["sku"]), None)
                if existing_item:
                    new_quantity = existing_item['quantity'] + quantity
                    if new_quantity > selected_row['stock']:
                        st.error(f"Vượt quá tồn kho! (Tối đa: {selected_row['stock']})")
                    else:
                        existing_item['quantity'] = new_quantity
                else:
                    st.session_state.cart.append({
                        "sku": selected_row["sku"],
                        "name": selected_row["name"],
                        "category_id": selected_row["category_id"], # Lưu category_id vào giỏ
                        "original_price": selected_row["price"],
                        "quantity": quantity
                    })
                st.rerun()