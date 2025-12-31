
import streamlit as st
import pandas as pd
from managers.product_manager import ProductManager
from managers.auth_manager import AuthManager

def render_product_catalog_page(prod_mgr: ProductManager, auth_mgr: AuthManager):
    st.header("🗂️ Danh mục Sản phẩm")

    user_info = auth_mgr.get_current_user_info()
    if not user_info:
        st.warning("Vui lòng đăng nhập để xem.")
        return

    user_role = user_info.get('role', 'user')
    is_admin = user_role == 'admin'
    is_manager_or_admin = user_role in ['admin', 'manager']

    # Initialize session state
    if 'editing_product_id' not in st.session_state:
        st.session_state.editing_product_id = None
    if 'deleting_product_id' not in st.session_state:
        st.session_state.deleting_product_id = None

    # --- TABS DEFINITION ---
    tab_titles = ["Quản lý Sản phẩm"]
    if is_admin:
        tab_titles.append("Thiết lập Danh mục & Đơn vị")
    tabs = st.tabs(tab_titles)

    # --- PRODUCT MANAGEMENT TAB ---
    with tabs[0]:
        # --- ADD/EDIT FORM ---
        if is_manager_or_admin:
            editing_product = prod_mgr.get_product_by_sku(st.session_state.editing_product_id) if st.session_state.editing_product_id else None
            form_title = "✏️ Chỉnh sửa Sản phẩm" if editing_product else "➕ Thêm Sản Phẩm Mới"
            
            with st.expander(form_title, expanded=st.session_state.editing_product_id is not None):
                categories = prod_mgr.get_categories()
                units = prod_mgr.get_units()
                cat_opts = {c['id']: f"{c['name']} ({c.get('prefix', 'SP')})" for c in categories}
                unit_opts = {u['id']: u['name'] for u in units}

                # Set form defaults for editing
                default_name = editing_product['name'] if editing_product else ""
                default_cat_index = list(cat_opts.keys()).index(editing_product['category_id']) if editing_product and editing_product.get('category_id') in cat_opts else 0
                default_unit_index = list(unit_opts.keys()).index(editing_product['unit_id']) if editing_product and editing_product.get('unit_id') in unit_opts else 0
                default_barcode = editing_product['barcode'] if editing_product else ""

                with st.form("product_form"):
                    st.text_input("SKU", value=(editing_product['sku'] if editing_product else "Tạo tự động"), disabled=True)
                    name = st.text_input("**Tên sản phẩm**", value=default_name)
                    col1, col2 = st.columns(2)
                    cat_id = col1.selectbox("**Danh mục**", options=list(cat_opts.keys()), format_func=lambda x: cat_opts.get(x, "N/A"), index=default_cat_index)
                    unit_id = col2.selectbox("**Đơn vị**", options=list(unit_opts.keys()), format_func=lambda x: unit_opts.get(x, "N/A"), index=default_unit_index)
                    barcode = st.text_input("Barcode", value=default_barcode)
                    image_file = st.file_uploader("Tải ảnh mới", type=['png', 'jpg', 'jpeg'])

                    submit_col, cancel_col = st.columns([1,5])
                    submitted = submit_col.form_submit_button(f"Lưu {('thay đổi' if editing_product else 'sản phẩm')}")
                    if editing_product:
                        if cancel_col.form_submit_button("Hủy", type="secondary"):
                            st.session_state.editing_product_id = None
                            st.rerun()

                    if submitted:
                        if not name or not cat_id:
                            st.error("Tên sản phẩm và Danh mục là bắt buộc!")
                        else:
                            data = {"name": name, "category_id": cat_id, "unit_id": unit_id, "barcode": barcode}
                            if image_file:
                                data['image_file'] = image_file # Pass the file object

                            with st.spinner("Đang xử lý..."):
                                if editing_product:
                                    success, msg = prod_mgr.update_product(editing_product['sku'], data)
                                else:
                                    success, msg = prod_mgr.create_product(data)

                            if success:
                                st.success(msg)
                                st.session_state.editing_product_id = None
                                st.rerun()
                            else:
                                st.error(msg)

        st.divider()

        # --- PRODUCT LIST ---
        st.subheader("Toàn bộ sản phẩm trong danh mục")
        products = prod_mgr.get_all_products(show_inactive=True)

        if not products: st.info("Chưa có sản phẩm nào."); return
        
        cats_df = pd.DataFrame(prod_mgr.get_categories()).set_index('id')
        cat_names = cats_df['name'].to_dict()

        h_cols = st.columns([1, 1, 3, 2, 1, 2])
        h_cols[0].write("**SKU**"); h_cols[1].write("**Ảnh**"); h_cols[2].write("**Tên**")
        h_cols[3].write("**Danh mục**"); h_cols[4].write("**Trạng thái**"); h_cols[5].write("**Hành động**")
        st.markdown("--- ", unsafe_allow_html=True)

        for p in products:
            p_cols = st.columns([1, 1, 3, 2, 1, 2])
            p_cols[0].write(p['sku'])
            p_cols[1].image(p['image_url'], width=60) if p.get('image_url') else p_cols[1].write("*")
            p_cols[2].write(p['name'])
            p_cols[3].write(cat_names.get(p.get('category_id'), "N/A"))

            # Status Toggle
            if is_admin:
                is_active = p.get('active', True)
                if p_cols[4].toggle("", value=is_active, key=f"active_{p['id']}", label_visibility="collapsed") != is_active:
                    prod_mgr.set_product_active_status(p['id'], not is_active)
                    st.success(f"Cập nhật trạng thái sản phẩm {p['sku']}")
                    st.rerun()
            else:
                p_cols[4].write("✅" if p.get('active', True) else "🔒")
            
            # Action Buttons
            if is_manager_or_admin and p_cols[5].button("✏️", key=f"edit_{p['id']}"):
                st.session_state.editing_product_id = p['id']
                st.rerun()
            if is_admin and p_cols[5].button("🗑️", key=f"delete_{p['id']}"):
                st.session_state.deleting_product_id = p['id']
                st.rerun()

            if is_admin and st.session_state.get('deleting_product_id') == p['id']:
                st.warning(f"Xóa vĩnh viễn **{p['name']} ({p['sku']})**? Hành động này không thể hoàn tác.")
                c1, c2 = st.columns(2)
                if c1.button("XÁC NHẬN", key=f"confirm_delete_{p['id']}"):
                    success, msg = prod_mgr.hard_delete_product(p['id'])
                    st.session_state.deleting_product_id = None
                    st.success(msg) if success else st.error(msg)
                    st.rerun()
                if c2.button("Hủy", key=f"cancel_delete_{p['id']}"):
                    st.session_state.deleting_product_id = None
                    st.rerun()
            st.markdown("--- ", unsafe_allow_html=True)

    # --- SETTINGS TAB ---
    if is_admin:
        with tabs[1]:
            col_cat, col_unit = st.columns(2)
            with col_cat:
                st.subheader("Quản lý Danh mục")
                with st.form("create_cat_form"):
                    # Form content for categories
                    st.dataframe(prod_mgr.get_categories(), hide_index=True)
            with col_unit:
                st.subheader("Quản lý Đơn vị tính")
                with st.form("create_unit_form"):
                    # Form content for units
                    st.dataframe(prod_mgr.get_units(), hide_index=True)
