import streamlit as st
import pandas as pd
from datetime import datetime

def render_pos_page():
    st.header("🛒 Bán hàng (POS)")

    # Lấy các manager từ session state
    product_mgr = st.session_state.product_mgr
    customer_mgr = st.session_state.customer_mgr
    inventory_mgr = st.session_state.inventory_mgr
    pos_mgr = st.session_state.pos_mgr
    current_branch_id = st.session_state.user['branch_id']

    # Khởi tạo/Lấy giỏ hàng từ session state
    if 'cart' not in st.session_state:
        st.session_state.cart = []

    # ---- 1. Giao diện ----
    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Thông tin đơn hàng")
        
        # Chọn khách hàng
        customers = customer_mgr.list_customers()
        customer_options = {c['id']: f"{c['name']} - {c['phone']}" for c in customers}
        customer_options["-"] = "Khách vãng lai"
        
        selected_customer_id = st.selectbox(
            "👤 Khách hàng", 
            options=list(customer_options.keys()),
            format_func=lambda x: customer_options[x],
            index=len(customer_options)-1 # Mặc định chọn khách vãng lai
        )

        st.divider()

        # Hiển thị giỏ hàng
        st.subheader("Giỏ hàng")
        if not st.session_state.cart:
            st.info("Giỏ hàng đang trống")
        else:
            # Chuyển giỏ hàng thành DataFrame để dễ hiển thị
            cart_df = pd.DataFrame(st.session_state.cart)
            st.dataframe(cart_df, use_container_width=True, hide_index=True)

            total_amount = cart_df['Thành tiền'].sum()
            st.metric("Tổng cộng", f"{total_amount:,.0f} VNĐ")

            # Nút thanh toán và xóa giỏ hàng
            pay_col, clear_col = st.columns(2)
            if pay_col.button("💳 Thanh toán", use_container_width=True, type="primary"):
                if not st.session_state.cart:
                    st.error("Giỏ hàng trống!")
                else:
                    order_data = {
                        "branch_id": current_branch_id,
                        "customer_id": selected_customer_id if selected_customer_id != "-" else None,
                        "items": [{
                            "sku": item["SKU"],
                            "name": item["Tên SP"],
                            "price": item["Đơn giá"],
                            "quantity": item["Số lượng"],
                            "total": item["Thành tiền"]
                        } for item in st.session_state.cart],
                        "total_amount": total_amount,
                        "created_by": st.session_state.user['id'],
                        "payment_method": "Cash" # Hardcoded for now
                    }
                    
                    with st.spinner("Đang xử lý đơn hàng..."):
                        success, result = pos_mgr.create_order(order_data)
                    
                    if success:
                        st.success(f"Tạo đơn hàng {result['id']} thành công!")
                        st.session_state.cart = [] # Xóa giỏ hàng
                        st.rerun()
                    else:
                        st.error(f"Lỗi: {result}")

            if clear_col.button("🗑️ Xóa giỏ hàng", use_container_width=True):
                st.session_state.cart = []
                st.rerun()

    with col2:
        st.subheader("Thêm sản phẩm")
        
        # Lấy danh sách sản phẩm và tồn kho
        products = product_mgr.list_products()
        branch_inventory = inventory_mgr.get_inventory_by_branch(current_branch_id)

        product_display_list = []
        for p in products:
            stock = branch_inventory.get(p['sku'], {}).get('stock_quantity', 0)
            if stock > 0: # Chỉ hiển thị sản phẩm còn hàng
                product_display_list.append({
                    "SKU": p['sku'], 
                    "Tên sản phẩm": p['name'], 
                    "Giá": p['price'], 
                    "Tồn kho": stock
                })
        
        if not product_display_list:
            st.warning("Tất cả sản phẩm tại chi nhánh này đã hết hàng.")
            return
        
        product_df = pd.DataFrame(product_display_list)
        
        # Chọn sản phẩm
        selected_product = st.selectbox(
            "Chọn hoặc tìm sản phẩm",
            options=product_df['Tên sản phẩm'] + " | Tồn kho: " + product_df['Tồn kho'].astype(str)
        )

        if selected_product:
            selected_name = selected_product.split(' |')[0]
            selected_row = product_df[product_df['Tên sản phẩm'] == selected_name].iloc[0]
            
            col_q, col_b = st.columns([1,2])
            quantity = col_q.number_input("Số lượng", min_value=1, max_value=int(selected_row['Tồn kho']), value=1)
            
            if col_b.button("Thêm vào giỏ", use_container_width=True):
                # Kiểm tra xem sản phẩm đã có trong giỏ chưa
                existing_item = next((item for item in st.session_state.cart if item["SKU"] == selected_row["SKU"]), None)
                if existing_item:
                    # Cập nhật số lượng
                    new_quantity = existing_item['Số lượng'] + quantity
                    if new_quantity > selected_row['Tồn kho']:
                        st.error(f"Vượt quá tồn kho! (Tối đa: {selected_row['Tồn kho']})")
                    else:
                        existing_item['Số lượng'] = new_quantity
                        existing_item['Thành tiền'] = new_quantity * existing_item['Đơn giá']
                else:
                    # Thêm mới
                    st.session_state.cart.append({
                        "SKU": selected_row["SKU"],
                        "Tên SP": selected_row["Tên sản phẩm"],
                        "Đơn giá": selected_row["Giá"],
                        "Số lượng": quantity,
                        "Thành tiền": selected_row["Giá"] * quantity
                    })
                st.rerun()
