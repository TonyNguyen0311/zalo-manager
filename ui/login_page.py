import streamlit as st
import time

def render_login():
    auth_mgr = st.session_state.auth_mgr
    branch_mgr = st.session_state.branch_mgr

    st.header("🔐 Đăng nhập hệ thống")

    # KIỂM TRA HỆ THỐNG CÓ USER CHƯA?
    if not auth_mgr.has_users():
        st.warning("⚠️ Hệ thống chưa có dữ liệu. Vui lòng khởi tạo Admin đầu tiên.")
        with st.form("setup_form"):
            st.subheader("1. Tạo Chi Nhánh Chính")
            br_name = st.text_input("Tên chi nhánh", "Cửa hàng Chính")
            br_addr = st.text_input("Địa chỉ", "Hà Nội")
            
            st.subheader("2. Tạo Tài khoản Admin")
            adm_user = st.text_input("Username", "admin")
            adm_pass = st.text_input("Password", type="password")
            adm_name = st.text_input("Tên hiển thị", "Quản trị viên")
            
            submitted = st.form_submit_button("Khởi tạo hệ thống")
            
            if submitted:
                if not adm_user or not adm_pass:
                    st.error("Vui lòng nhập đủ thông tin.")
                else:
                    with st.spinner("Đang khởi tạo..."):
                        # 1. Tạo Branch
                        branch = branch_mgr.create_branch(br_name, br_addr, "")
                        # 2. Tạo User Admin gắn với Branch đó
                        success, msg = auth_mgr.create_user(
                            username=adm_user,
                            password=adm_pass,
                            role="ADMIN",
                            branch_id=branch['id'],
                            display_name=adm_name
                        )
                        if success:
                            st.success("Khởi tạo thành công! Vui lòng đăng nhập.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Lỗi: {msg}")
        return

    # FORM ĐĂNG NHẬP BÌNH THƯỜNG
    with st.form("login_form"):
        username = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        btn_login = st.form_submit_button("Đăng nhập", use_container_width=True)

        if btn_login:
            user = auth_mgr.login(username, password)
            if user:
                st.session_state.user = user
                st.success(f"Xin chào {user['display_name']}!")
                st.rerun()
            else:
                st.error("Sai tên đăng nhập hoặc mật khẩu.")
