import streamlit as st
import pandas as pd

def render_report_page():
    st.header("📊 Báo cáo hiệu suất")

    # Lấy manager và thông tin user
    report_mgr = st.session_state.report_mgr
    user_role = st.session_state.user['role']
    user_branch_id = st.session_state.user['branch_id']
    branch_mgr = st.session_state.branch_mgr

    # ---- 1. Bộ lọc ----
    st.info("Lưu ý: Dữ liệu báo cáo được tổng hợp định kỳ và có thể có độ trễ nhất định.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        time_range_option = st.selectbox(
            "Khoảng thời gian",
            options=['7d', '30d', 'mtd', 'ytd'],
            format_func=lambda x: {'7d': '7 ngày qua', '30d': '30 ngày qua', 'mtd': 'Tháng này', 'ytd': 'Năm nay'}[x]
        )
    
    with col2:
        # Admin có thể xem tất cả chi nhánh hoặc từng chi nhánh
        if user_role == 'ADMIN':
            branches = branch_mgr.list_branches()
            branch_options = {b['id']: b['name'] for b in branches}
            branch_options["all"] = "Tất cả chi nhánh"
            
            selected_branch_id = st.selectbox(
                "Chi nhánh",
                options=list(branch_options.keys()),
                format_func=lambda x: branch_options[x],
                index=len(branch_options) - 1 # Mặc định là "Tất cả"
            )
            report_branch_id = selected_branch_id if selected_branch_id != 'all' else None
        else:
            # Staff chỉ xem được chi nhánh của mình
            report_branch_id = user_branch_id
            st.write(f"**Chi nhánh:** {branch_mgr.get_branch(user_branch_id)['name']}")

    # ---- 2. Tải dữ liệu từ Manager ----
    with st.spinner("Đang tải dữ liệu báo cáo..."):
        revenue_data = report_mgr.get_revenue_overview(report_branch_id, time_range_option)
        best_sellers_data = report_mgr.get_best_selling_products(report_branch_id, limit=10)

    # ---- 3. Hiển thị ----
    st.subheader("Tổng quan Doanh thu")
    if not revenue_data['order_count'] > 0:
        st.warning("Không có dữ liệu doanh thu trong khoảng thời gian đã chọn.")
    else:
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Tổng doanh thu", f"{revenue_data['total_revenue']:,.0f} VNĐ")
        kpi2.metric("Tổng số đơn hàng", f"{revenue_data['order_count']}")
        avg_revenue = revenue_data['total_revenue'] / revenue_data['order_count']
        kpi3.metric("Doanh thu trung bình/đơn", f"{avg_revenue:,.0f} VNĐ")

        # Biểu đồ doanh thu theo ngày
        if revenue_data['daily_revenue']:
            daily_df = pd.DataFrame(revenue_data['daily_revenue'], columns=['Ngày', 'Doanh thu'])
            daily_df['Ngày'] = pd.to_datetime(daily_df['Ngày'])
            daily_df = daily_df.set_index('Ngày')
            st.line_chart(daily_df)

    st.divider()

    st.subheader("Top 10 Sản phẩm bán chạy")
    if not best_sellers_data:
        st.warning("Không có dữ liệu về sản phẩm bán chạy.")
    else:
        bestseller_df = pd.DataFrame(best_sellers_data)
        bestseller_df.columns = ["SKU", "Tên Sản phẩm", "Số lượng đã bán"]
        st.dataframe(bestseller_df, use_container_width=True, hide_index=True)
