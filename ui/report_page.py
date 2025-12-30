
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Giả định các manager được truyền vào đúng cách
from managers.report_manager import ReportManager
from managers.branch_manager import BranchManager
from managers.auth_manager import AuthManager 

def render_report_page(report_mgr: ReportManager, branch_mgr: BranchManager, auth_mgr: AuthManager):
    st.title("📊 Báo cáo & Phân tích")

    # Lấy thông tin người dùng hiện tại từ session state
    if 'user' not in st.session_state or not st.session_state.user:
        st.warning("Vui lòng đăng nhập để xem báo cáo.")
        return
    user_info = st.session_state.user

    # --- LOGIC PHÂN QUYỀN VÀ LỌC DỮ LIỆU (giữ nguyên) ---
    user_role = user_info.get('role', 'staff')
    user_branches = user_info.get('branch_ids', [])
    all_branches_map = {b['id']: b['name'] for b in branch_mgr.list_branches(active_only=False)} # Sửa ở đây
    allowed_branches_map = {}
    if user_role == 'admin':
        allowed_branches_map = all_branches_map
    else:
        for branch_id in user_branches:
            if branch_id in all_branches_map:
                allowed_branches_map[branch_id] = all_branches_map[branch_id]

    if not allowed_branches_map:
        st.error("Tài khoản của bạn chưa được gán cho chi nhánh nào. Vui lòng liên hệ quản trị viên.")
        return

    # --- GIAO DIỆN LỌC ---
    report_type = st.selectbox(
        "Chọn loại báo cáo",
        ["Báo cáo Doanh thu", "Phân tích Lợi nhuận", "Báo cáo Tồn kho"]
    )

    # Lọc theo chi nhánh
    selected_branch_ids = st.multiselect(
        "Chọn chi nhánh",
        options=list(allowed_branches_map.keys()),
        format_func=lambda x: allowed_branches_map[x],
        default=list(allowed_branches_map.keys()) # Mặc định chọn tất cả chi nhánh được phép
    )

    # Lọc theo thời gian
    c1, c2 = st.columns(2)
    today = datetime.now()
    start_date = c1.date_input("Từ ngày", today - timedelta(days=30))
    end_date = c2.date_input("Đến ngày", today)

    if st.button("Xem báo cáo", type="primary"):
        if not selected_branch_ids:
            st.warning("Vui lòng chọn ít nhất một chi nhánh.")
            return
        
        # Convert date to datetime objects for the manager
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        # --- LOGIC GỌI MANAGER TƯƠNG ỨNG ---
        with st.spinner("Đang tải dữ liệu..."):
            if report_type == "Báo cáo Doanh thu":
                # Giả định manager có hàm get_revenue_report
                success, data, message = report_mgr.get_revenue_report(start_datetime, end_datetime, selected_branch_ids)
                if success:
                    st.subheader("Báo cáo tổng quan doanh thu")
                    # Hiển thị các chỉ số chính (KPIs)
                    kpi_cols = st.columns(4)
                    kpi_cols[0].metric("Tổng Doanh thu", f"{data['total_revenue']:,} VNĐ")
                    kpi_cols[1].metric("Tổng Lợi nhuận gộp", f"{data['total_profit']:,} VNĐ")
                    kpi_cols[2].metric("Số lượng hóa đơn", f"{data['total_orders']}")
                    kpi_cols[3].metric("Giá trị trung bình/đơn", f"{data['average_order_value']:,} VNĐ")
                    
                    # Hiển thị biểu đồ
                    st.write("**Doanh thu theo ngày**")
                    st.line_chart(data['revenue_by_day'])

                    st.write("**Top 5 sản phẩm bán chạy nhất (theo doanh thu)**")
                    st.dataframe(data['top_products_by_revenue'])
                else:
                    st.error(f"Lỗi khi lấy báo cáo: {message}")

            elif report_type == "Phân tích Lợi nhuận":
                st.info("Tính năng đang được phát triển.")
                # success, data, message = report_mgr.get_profit_analysis(start_datetime, end_datetime, selected_branch_ids)
                # if success:
                #     # Display profit analysis
                #     pass
                # else:
                #     st.error(message)

            elif report_type == "Báo cáo Tồn kho":
                st.info("Tính năng đang được phát triển.")
                # success, data, message = report_mgr.get_inventory_report(selected_branch_ids)
                # if success:
                #     # Display inventory report
                #     pass
                # else:
                #     st.error(message)
