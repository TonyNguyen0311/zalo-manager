
import streamlit as st
from managers.auth_manager import AuthManager
from managers.branch_manager import BranchManager

def render_login_page(auth_mgr: AuthManager, branch_mgr: BranchManager):
    st.set_page_config(layout="centered")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Đăng nhập hệ thống")

        # ======== TẠM THỜI HIỂN THỊ FORM KHỞI TẠO ========
        st.warning("⚠️ Chế độ thiết lập Admin tạm thời. Vui lòng tạo tài khoản Admin mới.")
        with st.form("setup_form"):
            st.subheader("Tạo Tài khoản Admin Mới")
            adm_user = st.text_input("Username mới", "admin")
            adm_pass = st.text_input("Password mới (ít nhất 6 ký tự)", type="password")
            adm_name = st.text_input("Tên hiển thị", "Quản trị viên")
            
            submitted = st.form_submit_button("Khởi tạo Admin")
            
            if submitted:
                if len(adm_pass) < 6:
                    st.error("Mật khẩu phải có ít nhất 6 ký tự.")
                elif not all([adm_user, adm_pass, adm_name]):
                    st.error("Vui lòng nhập đủ thông tin cho tài khoản Admin.")
                else:
                    try:
                        # FIX: Admin user does not need a specific branch.
                        # The role 'admin' grants access to all branches.
                        user_data = {
                            "username": adm_user,
                            "display_name": adm_name,
                            "role": "admin",
                            "branch_ids": [] # Empty list for admin
                        }
                        auth_mgr.create_user_record(user_data, adm_pass)
                        st.success(f"🎉 Đã tạo thành công tài khoản admin '{adm_user}'. Vui lòng tải lại trang và đăng nhập bằng form bên dưới.")
                        st.balloons()
                    except ValueError as e:
                        st.error(f"Lỗi: {e}")
                    except Exception as e:
                        st.error(f"Đã có lỗi xảy ra khi tạo tài khoản: {e}")

        st.divider()
        # ==========================================================

        # Form đăng nhập bình thường
        with st.form("login_form"):
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type="password")
            
            login_button = st.form_submit_button("Đăng nhập")
            
            if login_button:
                user = auth_mgr.login(username, password)
                if user:
                    st.success("Đăng nhập thành công!")
                    st.rerun() 
                else:
                    st.error("Sai tên đăng nhập hoặc mật khẩu.")
