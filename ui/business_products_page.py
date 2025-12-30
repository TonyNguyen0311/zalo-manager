
import streamlit as st
import pandas as pd

# Import managers
from managers.auth_manager import AuthManager
from managers.branch_manager import BranchManager
from managers.product_manager import ProductManager
from managers.price_manager import PriceManager

def render_business_products_page(auth_mgr: AuthManager, branch_mgr: BranchManager, prod_mgr: ProductManager, price_mgr: PriceManager):
    st.header("🛍️ Sản phẩm Kinh doanh")

    # --- 1. PHÂN QUYỀN & CHỌN CHI NHÁNH --- #
    user_info = auth_mgr.get_current_user_info()
    user_role = user_info.get('role', 'staff')

    if user_role not in ['admin', 'manager']:
        st.warning("Bạn không có quyền truy cập chức năng này.")
        return

    # Lấy danh sách chi nhánh được phép truy cập
    user_branches = user_info.get('branch_ids', [])
    all_branches_map = {b['id']: b['name'] for b in branch_mgr.get_branches()}
    allowed_branches_map = {branch_id: all_branches_map[branch_id] for branch_id in user_branches if branch_id in all_branches_map}
    if user_role == 'admin':
        allowed_branches_map = all_branches_map

    if not allowed_branches_map:
        st.warning("Tài khoản của bạn chưa được gán vào chi nhánh nào. Vui lòng liên hệ Admin.")
        return

    # Chọn chi nhánh để quản lý
    if len(allowed_branches_map) > 1:
        selected_branch_id = st.selectbox(
            "Chọn chi nhánh để quản lý", 
            options=list(allowed_branches_map.keys()), 
            format_func=lambda x: allowed_branches_map[x]
        )
    else:
        selected_branch_id = list(allowed_branches_map.keys())[0]
        st.subheader(f"Chi nhánh: {allowed_branches_map[selected_branch_id]}")

    if not selected_branch_id:
        st.stop()

    st.divider()

    # --- 2. LẤY DỮ LIỆU SẢN PHẨM & GIÁ --- #
    all_catalog_products = prod_mgr.list_products()
    all_prices = price_mgr.get_all_prices() # Giả định hàm này tồn tại để tối ưu

    # Lọc giá cho chi nhánh đã chọn
    prices_in_branch = {p['sku']: p for p in all_prices if p.get('branch_id') == selected_branch_id}
    listed_skus = prices_in_branch.keys()

    # Phân loại sản phẩm đã niêm yết và chưa niêm yết
    listed_products = [p for p in all_catalog_products if p['sku'] in listed_skus]
    unlisted_products = [p for p in all_catalog_products if p['sku'] not in listed_skus]

    # --- 3. NIÊM YẾT SẢN PHẨM MỚI --- #
    with st.expander("➕ Niêm yết sản phẩm mới vào chi nhánh"):
        if not unlisted_products:
            st.info("Tất cả sản phẩm trong danh mục đã được niêm yết tại chi nhánh này.")
        else:
            with st.form("form_list_product"):
                product_to_list = st.selectbox("Chọn sản phẩm từ danh mục", options=unlisted_products, format_func=lambda p: f"{p['name']} ({p['sku']})")
                new_price = st.number_input("Nhập giá bán cho chi nhánh này (VNĐ)", min_value=0, step=1000)
                
                if st.form_submit_button("Niêm yết"):
                    if product_to_list and new_price > 0:
                        sku = product_to_list['sku']
                        price_mgr.set_price(sku, selected_branch_id, new_price)
                        # Lưu trạng thái kinh doanh mặc định là active
                        price_mgr.set_business_status(sku, selected_branch_id, True)
                        st.success(f"Đã niêm yết thành công sản phẩm \"{product_to_list['name']}\" với giá {new_price:,} VNĐ.")
                        st.rerun()
                    else:
                        st.error("Vui lòng chọn sản phẩm và nhập giá bán lớn hơn 0.")

    st.divider()

    # --- 4. DANH SÁCH SẢN PHẨM ĐANG KINH DOANH --- #
    st.subheader("Sản phẩm đang kinh doanh tại chi nhánh")
    if not listed_products:
        st.info("Chưa có sản phẩm nào được niêm yết tại chi nhánh này.")
    else:
        for prod in listed_products:
            sku = prod['sku']
            price_info = prices_in_branch.get(sku, {})
            current_price = price_info.get('price', 0)
            is_active = price_info.get('is_active', True)

            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.markdown(f"**{prod['name']}** ({prod['sku']})")
                with col2:
                    new_price = st.number_input("Giá bán (VNĐ)", value=current_price, key=f"price_{sku}", label_visibility="collapsed", min_value=0, step=1000)
                with col3:
                    new_status = st.checkbox("Đang bán", value=is_active, key=f"status_{sku}")
                with col4:
                    if st.button("Cập nhật", key=f"update_{sku}"):
                        # Cập nhật giá
                        if new_price != current_price:
                            price_mgr.set_price(sku, selected_branch_id, new_price)
                        # Cập nhật trạng thái
                        if new_status != is_active:
                            price_mgr.set_business_status(sku, selected_branch_id, new_status)
                        st.toast(f"Đã cập nhật {prod['name']}", icon="✅")
                        st.rerun()
                st.divider()
