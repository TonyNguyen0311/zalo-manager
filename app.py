
import streamlit as st
import json
import os
from managers.firebase_client import FirebaseClient

# Import managers
from managers.auth_manager import AuthManager
from managers.branch_manager import BranchManager
from managers.product_manager import ProductManager
from managers.inventory_manager import InventoryManager
from managers.customer_manager import CustomerManager
from managers.pos_manager import POSManager
from managers.report_manager import ReportManager
from managers.session_manager import is_session_active, check_remember_me
from managers.settings_manager import SettingsManager
from managers.promotion_manager import PromotionManager
from managers.cost_manager import CostManager
from managers.price_manager import PriceManager

# Import UI pages - Cấu trúc mới
from ui.login_page import render_login
from ui.pos_page import render_pos_page
from ui.report_page import render_report_page
from ui.settings_page import render_settings_page
from ui.promotions_page import render_promotions_page
from ui.cost_page import render_cost_page
from ui.inventory_page import render_inventory_page
from ui.user_management_page import render_user_management_page
from ui.product_catalog_page import render_product_catalog_page
from ui.business_products_page import render_business_products_page

st.set_page_config(layout="wide")

# --- ĐỊNH NGHĨA QUYỀN TRUY CẬP MENU ---
MENU_PERMISSIONS = {
    "admin": [
        "Báo cáo & Phân tích",
        "Bán hàng (POS)",
        "Sản phẩm Kinh doanh",
        "Quản lý Kho",
        "Quản lý Chi phí",
        "Danh mục Sản phẩm",
        "Quản lý Khuyến mãi",
        "Quản lý Người dùng",
        "Quản trị Hệ thống",
    ],
    "manager": [
        "Báo cáo & Phân tích",
        "Bán hàng (POS)",
        "Sản phẩm Kinh doanh",
        "Quản lý Kho",
        "Quản lý Chi phí",
    ],
    "staff": [
        "Bán hàng (POS)",
    ]
}

def init_managers():
    if "firebase" not in st.secrets or "credentials_json" not in st.secrets.firebase:
        st.error("Firebase secrets not found...")
        return False
    if 'firebase_client' not in st.session_state:
        try:
            creds_dict = json.loads(st.secrets["firebase"]["credentials_json"])
            st.session_state.firebase_client = FirebaseClient(creds_dict)
        except (json.JSONDecodeError, KeyError):
            st.error("Failed to parse Firebase credentials...")
            return False
    fb_client = st.session_state.firebase_client
    if 'auth_mgr' not in st.session_state: st.session_state.auth_mgr = AuthManager(fb_client)
    if 'branch_mgr' not in st.session_state: st.session_state.branch_mgr = BranchManager(fb_client)
    if 'product_mgr' not in st.session_state: st.session_state.product_mgr = ProductManager(fb_client)
    if 'inventory_mgr' not in st.session_state: st.session_state.inventory_mgr = InventoryManager(fb_client)
    if 'customer_mgr' not in st.session_state: st.session_state.customer_mgr = CustomerManager(fb_client)
    if 'settings_mgr' not in st.session_state: st.session_state.settings_mgr = SettingsManager(fb_client)
    if 'promotion_mgr' not in st.session_state: st.session_state.promotion_mgr = PromotionManager(fb_client)
    if 'cost_mgr' not in st.session_state: st.session_state.cost_mgr = CostManager(fb_client)
    if 'price_mgr' not in st.session_state: st.session_state.price_mgr = PriceManager(fb_client)
    if 'report_mgr' not in st.session_state:
        st.session_state.report_mgr = ReportManager(fb_client, st.session_state.cost_mgr)
    if 'pos_mgr' not in st.session_state:
        st.session_state.pos_mgr = POSManager(
            firebase_client=fb_client,
            inventory_mgr=st.session_state.inventory_mgr,
            customer_mgr=st.session_state.customer_mgr,
            promotion_mgr=st.session_state.promotion_mgr,
            price_mgr=st.session_state.price_mgr,
            cost_mgr=st.session_state.cost_mgr
        )
    return True

def display_sidebar():
    user_info = st.session_state.user
    st.sidebar.success(f"Xin chào, {user_info.get('display_name', 'Người dùng')}!")
    
    # <<< SỬA LỖI 1: Chuyển vai trò về chữ thường để khớp với key của MENU_PERMISSIONS
    role = user_info.get('role', 'staff').lower()
    
    st.sidebar.write(f"Vai trò: **{role.upper()}**")
    branch_ids = user_info.get('branch_ids', [])
    if role == 'admin':
        st.sidebar.write("Quyền truy cập: **Toàn bộ hệ thống**")
    elif branch_ids:
        branch_names = [st.session_state.branch_mgr.get_branch_name(b_id) for b_id in branch_ids]
        st.sidebar.write(f"Chi nhánh: **{', '.join(branch_names)}**")

    available_pages = MENU_PERMISSIONS.get(role, [])
    if not available_pages:
        st.sidebar.warning("Không có chức năng nào được cấp phép.")

    # Sắp xếp lại thứ tự cho hợp lý
    ordered_pages = []
    preferred_order = ["Báo cáo & Phân tích", "Bán hàng (POS)"]
    for item in preferred_order:
        if item in available_pages:
            ordered_pages.append(item)
            available_pages.remove(item)
    ordered_pages.extend(available_pages) # Thêm các trang còn lại

    page = st.sidebar.selectbox("Chức năng", ordered_pages, key="main_menu")
    
    if st.sidebar.button("Đăng xuất"):
        if os.path.exists(".remember_me"):
            os.remove(".remember_me")
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    return page

def main():
    if not init_managers():
        return

    if not is_session_active() and not check_remember_me():
        render_login()
        return
    
    page = display_sidebar()

    # <<< SỬA LỖI 2: Các hàm render không còn nhận tham số trực tiếp
    page_renderers = {
        "Bán hàng (POS)": render_pos_page,
        "Báo cáo & Phân tích": render_report_page,
        "Quản lý Kho": render_inventory_page,
        "Quản lý Chi phí": render_cost_page,
        "Quản lý Khuyến mãi": render_promotions_page,
        "Quản lý Người dùng": render_user_management_page,
        "Quản trị Hệ thống": render_settings_page,
        "Danh mục Sản phẩm": render_product_catalog_page,
        "Sản phẩm Kinh doanh": render_business_products_page,
    }

    renderer = page_renderers.get(page)
    if renderer:
        renderer()
    else:
        st.warning(f"Trang '{page}' đang trong quá trình phát triển hoặc đã bị loại bỏ.")

if __name__ == "__main__":
    main()
