
import streamlit as st
from managers.settings_manager import SettingsManager
from managers.auth_manager import AuthManager

def render_settings_page(settings_mgr: SettingsManager, auth_mgr: AuthManager):
    st.title("⚙️ Quản trị Hệ thống")

    user_info = auth_mgr.get_current_user_info()
    if not user_info or user_info.get('role', '').lower() != 'admin':
        st.error("Truy cập bị từ chối. Chức năng này chỉ dành cho Quản trị viên.")
        return

    # Cấu trúc tab để dễ dàng mở rộng trong tương lai
    tab1, tab2, tab3 = st.tabs(["Chi nhánh", "Thông tin Kinh doanh", "Cài đặt khác"])

    # ===================================
    # TAB 1: QUẢN LÝ CHI NHÁNH
    # ===================================
    with tab1:
        st.subheader("Quản lý Chi nhánh")
        branch_mgr = st.session_state.branch_mgr # Lấy manager từ session state

        # Form thêm chi nhánh mới
        with st.form("add_branch_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                branch_name = st.text_input("Tên chi nhánh")
            with c2:
                branch_address = st.text_input("Địa chỉ")
            if st.form_submit_button("Thêm chi nhánh", type="primary"):
                if branch_name:
                    try:
                        branch_mgr.create_branch(branch_name, branch_address)
                        st.success(f"Đã thêm chi nhánh '{branch_name}'")
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
                else:
                    st.warning("Tên chi nhánh không được để trống.")

        st.divider()
        
        # Danh sách chi nhánh hiện có
        st.write("**Các chi nhánh hiện có:**")
        branches = branch_mgr.list_branches()
        if not branches:
            st.info("Chưa có chi nhánh nào được tạo.")
        else:
            for branch in branches:
                with st.container(border=True):
                    b_c1, b_c2 = st.columns([0.8, 0.2])
                    with b_c1:
                        st.text_input("Tên", value=branch['name'], key=f"name_{branch['id']}", disabled=True)
                        st.text_input("Địa chỉ", value=branch.get('address', ''), key=f"addr_{branch['id']}", disabled=True)
                    with b_c2:
                        if st.button("Xóa", key=f"del_{branch['id']}", use_container_width=True):
                            # Thêm confirm box trước khi xóa
                            st.session_state[f'confirm_delete_{branch['id']}'] = True
            
                # Logic cho confirmation dialog
                if st.session_state.get(f'confirm_delete_{branch['id']}'):
                    st.warning(f"Bạn có chắc muốn xóa chi nhánh '{branch['name']}'? Hành động này không thể hoàn tác.")
                    cd_c1, cd_c2 = st.columns(2)
                    if cd_c1.button("Xác nhận Xóa", key=f"confirm_btn_{branch['id']}", type="primary"):
                        try:
                            # Cần kiểm tra xem chi nhánh có đang được sử dụng không
                            branch_mgr.delete_branch(branch['id'])
                            st.success("Đã xóa thành công!")
                            del st.session_state[f'confirm_delete_{branch['id']}'] 
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi xóa: {e}")
                    if cd_c2.button("Hủy", key=f"cancel_btn_{branch['id']}"):
                        del st.session_state[f'confirm_delete_{branch['id']}']
                        st.rerun()

    # ===================================
    # TAB 2: THÔNG TIN KINH DOANH
    # ===================================
    with tab2:
        st.subheader("Thông tin Doanh nghiệp/Cửa hàng")
        current_settings = settings_mgr.get_settings()
        business_info = current_settings.get('business_info', {})

        with st.form("business_info_form"):
            name = st.text_input("Tên doanh nghiệp", value=business_info.get('name', ''))
            tax_code = st.text_input("Mã số thuế", value=business_info.get('tax_code', ''))
            phone = st.text_input("Số điện thoại", value=business_info.get('phone', ''))
            address = st.text_area("Địa chỉ đăng ký kinh doanh", value=business_info.get('address', ''))

            if st.form_submit_button("Lưu thông tin", type="primary"):
                new_info = {
                    'name': name,
                    'tax_code': tax_code,
                    'phone': phone,
                    'address': address
                }
                settings_mgr.save_setting('business_info', new_info)
                st.success("Đã cập nhật thông tin doanh nghiệp.")

    # ===================================
    # TAB 3: CÀI ĐẶT KHÁC
    # ===================================
    with tab3:
        st.subheader("Cài đặt phiên đăng nhập")
        current_settings = settings_mgr.get_settings()

        timeout_options = {
            "30 phút": 30,
            "60 phút (mặc định)": 60,
            "120 phút": 120,
            "Không bao giờ": "never"
        }

        current_timeout_val = current_settings.get('session_timeout_minutes', 60)
        current_option_key = next((key for key, value in timeout_options.items() if value == current_timeout_val), "60 phút (mặc định)")

        new_timeout_key = st.selectbox(
            "Thời gian tự động đăng xuất khi không hoạt động",
            options=list(timeout_options.keys()),
            index=list(timeout_options.keys()).index(current_option_key)
        )

        if st.button("Lưu cài đặt phiên", type="primary"):
            new_timeout_val = timeout_options[new_timeout_key]
            settings_mgr.save_setting('session_timeout_minutes', new_timeout_val)
            st.success("Đã lưu cài đặt phiên đăng nhập!")
