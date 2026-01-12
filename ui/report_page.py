
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# Import managers
from managers.report_manager import ReportManager
from managers.branch_manager import BranchManager
from managers.auth_manager import AuthManager

# Import UI utils and formatters
from ui._utils import render_page_title, render_section_header, render_sub_header
from utils.formatters import format_currency, format_number

def render_report_page(report_mgr: ReportManager, branch_mgr: BranchManager, auth_mgr: AuthManager):
    # 1. RENDER PAGE HEADER
    render_page_title("Báo cáo & Phân tích")

    # 2. USER PERMISSIONS & DATA ACCESS
    user_info = auth_mgr.get_current_user_info()
    if not user_info:
        st.warning("Vui lòng đăng nhập để xem báo cáo.")
        return

    user_role = user_info.get('role', 'staff')
    user_branches = user_info.get('branch_ids', [])
    all_branches_map = {b['id']: b['name'] for b in branch_mgr.list_branches(active_only=False)}

    if user_role == 'admin':
        allowed_branches_map = all_branches_map
    else:
        allowed_branches_map = {bid: name for bid, name in all_branches_map.items() if bid in user_branches}

    if not allowed_branches_map:
        st.error("Tài khoản của bạn chưa được gán cho chi nhánh nào. Vui lòng liên hệ quản trị viên.")
        return

    # 3. FILTERING UI
    with st.expander("⚙️ Tùy chọn báo cáo", expanded=True):
        report_type = st.selectbox(
            "Chọn loại báo cáo",
            ["Báo cáo Doanh thu", "Báo cáo Tồn kho", "Phân tích Lợi nhuận"],
            key="report_type_selector"
        )

        is_inventory_report = report_type == "Báo cáo Tồn kho"

        if is_inventory_report:
            selected_branch_ids = st.multiselect(
                "Chọn chi nhánh",
                options=list(allowed_branches_map.keys()),
                format_func=lambda x: allowed_branches_map[x],
                default=list(allowed_branches_map.keys()),
                key="inv_branch_multiselect"
            )
        else:
            col1, col2 = st.columns(2)
            today = datetime.now()
            start_date = col1.date_input("Từ ngày", today - timedelta(days=30), key="date_start")
            end_date = col2.date_input("Đến ngày", today, key="date_end")
            selected_branch_ids = st.multiselect(
                "Chọn chi nhánh",
                options=list(allowed_branches_map.keys()),
                format_func=lambda x: allowed_branches_map[x],
                default=list(allowed_branches_map.keys()),
                key="std_branch_multiselect"
            )

        if st.button("📈 Xem báo cáo", type="primary", use_container_width=True):
            if not selected_branch_ids:
                st.warning("Vui lòng chọn ít nhất một chi nhánh.")
            else:
                st.session_state.run_report = True
                st.session_state.report_type = report_type
                st.session_state.selected_branch_ids = selected_branch_ids
                if not is_inventory_report:
                    st.session_state.start_date = start_date
                    st.session_state.end_date = end_date

    st.divider()

    # 4. REPORT DISPLAY LOGIC
    if not st.session_state.get('run_report', False):
        st.info("Chọn các tùy chọn và nhấn 'Xem báo cáo' để bắt đầu.")
        return

    report_type = st.session_state.report_type
    selected_branch_ids = st.session_state.selected_branch_ids

    with st.spinner("Đang xử lý và tải dữ liệu báo cáo..."):
        # --- BÁO CÁO DOANH THU -- -
        if report_type == "Báo cáo Doanh thu":
            start_datetime = datetime.combine(st.session_state.start_date, datetime.min.time())
            end_datetime = datetime.combine(st.session_state.end_date, datetime.max.time())
            result = report_mgr.get_revenue_report(start_datetime, end_datetime, selected_branch_ids)
            
            if result["success"] and result.get("data"):
                data = result["data"]
                render_section_header("Tổng quan Doanh thu")
                kpi_cols = st.columns(4)
                kpi_cols[0].metric("Tổng Doanh thu", format_currency(data.get('total_revenue', 0)))
                kpi_cols[1].metric("Tổng Lợi nhuận gộp", format_currency(data.get('total_profit', 0)))
                kpi_cols[2].metric("Số lượng hóa đơn", format_number(data.get('total_orders', 0)))
                kpi_cols[3].metric("Giá trị/hóa đơn", format_currency(data.get('average_order_value', 0)))
                
                st.divider()
                render_sub_header("Biểu đồ doanh thu theo ngày")
                revenue_df = data.get('revenue_by_day')
                if revenue_df is not None and not revenue_df.empty:
                    st.line_chart(revenue_df)
                else:
                    st.info("Không có dữ liệu doanh thu trong khoảng thời gian này.")
                
                render_sub_header("Top 5 sản phẩm bán chạy nhất (theo doanh thu)")
                top_products_df = data.get('top_products_by_revenue')
                if top_products_df is not None and not top_products_df.empty:
                    st.dataframe(top_products_df.style.format({'Doanh thu': format_currency, 'Lợi nhuận': format_currency, 'Số lượng': format_number}), use_container_width=True)
                else:
                    st.info("Không có dữ liệu về sản phẩm bán chạy.")
            else:
                st.error(f"Lỗi khi lấy báo cáo: {result.get('message', 'Lỗi không xác định')}")

        # --- BÁO CÁO TỒN KHO -- -
        elif report_type == "Báo cáo Tồn kho":
            result = report_mgr.get_inventory_report(selected_branch_ids)
            if result["success"] and result.get("data"):
                report_data = result["data"]
                render_section_header("Tổng quan Tồn kho")
                kpi_cols = st.columns(2)
                kpi_cols[0].metric("Tổng giá trị tồn kho", format_currency(report_data.get('total_inventory_value', 0)))
                kpi_cols[1].metric("Tổng số lượng sản phẩm", format_number(report_data.get('total_inventory_items', 0)))
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    render_sub_header("Top 10 sản phẩm giá trị tồn kho cao nhất")
                    top_prod_df = report_data.get('top_products_by_value_df')
                    if top_prod_df is not None and not top_prod_df.empty:
                        st.dataframe(top_prod_df.style.format({'total_value': format_currency, 'total_quantity': format_number}), use_container_width=True)
                    else:
                        st.info("Không có dữ liệu.")
                with col2:
                    render_sub_header("Cảnh báo: Sản phẩm sắp hết hàng (<10)")
                    low_stock_df = report_data.get('low_stock_items_df')
                    if low_stock_df is not None and not low_stock_df.empty:
                        st.dataframe(low_stock_df[['product_name', 'quantity', 'branch_id']].rename(columns={'product_name': 'Tên sản phẩm', 'quantity': 'Tồn kho', 'branch_id': 'Chi nhánh'}), use_container_width=True)
                    else:
                        st.success("Tốt! Không có sản phẩm nào sắp hết hàng.")
                with st.expander("Xem chi tiết toàn bộ tồn kho"):
                    detail_df = report_data.get('inventory_details_df')
                    if detail_df is not None and not detail_df.empty:
                        detail_df['branch_name'] = detail_df['branch_id'].map(allowed_branches_map)
                        st.dataframe(detail_df[['product_name', 'branch_name', 'quantity', 'cost_price', 'total_value']].style.format({'quantity': format_number, 'cost_price': format_currency, 'total_value': format_currency}), use_container_width=True)
            else:
                st.error(f"Lỗi khi tạo báo cáo tồn kho: {result.get('message')}")

        # --- PHÂN TÍCH LỢI NHUẬN -- -
        elif report_type == "Phân tích Lợi nhuận":
            start_datetime = datetime.combine(st.session_state.start_date, datetime.min.time())
            end_datetime = datetime.combine(st.session_state.end_date, datetime.max.time())
            result = report_mgr.get_profit_analysis_report(start_datetime, end_datetime, selected_branch_ids)
            if result.get('success') and result.get('data'):
                report_data = result['data']
                product_df = report_data['product_profit_df']
                category_df = report_data['category_profit_df']
                render_section_header("Phân tích Lợi nhuận")
                tab1, tab2 = st.tabs(["Lợi nhuận theo Sản phẩm", "Lợi nhuận theo Danh mục"])
                with tab1:
                    render_sub_header("Top 10 sản phẩm lợi nhuận cao nhất")
                    top_10_profit_products = product_df.head(10)
                    fig = px.bar(top_10_profit_products, x='product_name', y='total_profit', title="Lợi nhuận theo sản phẩm", labels={'product_name':'Sản phẩm', 'total_profit':'Lợi nhuận'})
                    st.plotly_chart(fig, use_container_width=True)
                    with st.expander("Xem chi tiết lợi nhuận theo sản phẩm"):
                        st.dataframe(product_df.style.format({'total_revenue': format_currency, 'total_profit': format_currency, 'total_quantity_sold': format_number, 'profit_margin': '{:.2f}%'}), use_container_width=True)
                with tab2:
                    render_sub_header("Phân bổ lợi nhuận theo danh mục")
                    fig_cat = px.pie(category_df, names='category_name', values='total_profit', title="Tỷ trọng lợi nhuận theo danh mục")
                    st.plotly_chart(fig_cat, use_container_width=True)
                    st.dataframe(category_df.style.format({'total_revenue': format_currency, 'total_profit': format_currency, 'profit_margin': '{:.2f}%'}), use_container_width=True)
            else:
                st.warning(result.get('message', "Không thể tạo báo cáo phân tích lợi nhuận."))

    # Reset flag after rendering the report to avoid re-running automatically
    st.session_state.run_report = False
