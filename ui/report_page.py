import streamlit as st
import pandas as pd
import altair as alt

def render_report_page():
    st.header("📊 Báo cáo hiệu suất")

    # Lấy manager và thông tin user
    report_mgr = st.session_state.report_mgr
    user_info = st.session_state.user
    user_role = user_info['role']
    user_branch_id = user_info['branch_id']
    branch_mgr = st.session_state.branch_mgr

    # ---- 1. Bộ lọc chung ----
    st.info("Lưu ý: Dữ liệu báo cáo được tổng hợp định kỳ và có thể có độ trễ nhất định.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        time_range_option = st.selectbox(
            "Khoảng thời gian",
            options=['7d', '30d', 'mtd', 'ytd'],
            format_func=lambda x: {'7d': '7 ngày qua', '30d': '30 ngày qua', 'mtd': 'Tháng này', 'ytd': 'Năm nay'}[x],
            key="report_time_range"
        )
    
    with col2:
        if user_role == 'ADMIN':
            branches = branch_mgr.list_branches()
            branch_options = {b['id']: b['name'] for b in branches}
            branch_options["all"] = "Tất cả chi nhánh"
            
            selected_branch_id = st.selectbox(
                "Chi nhánh",
                options=list(branch_options.keys()),
                format_func=lambda x: branch_options[x],
                index=len(branch_options) - 1, 
                key="report_branch_select"
            )
            report_branch_id = selected_branch_id if selected_branch_id != 'all' else None
        else:
            report_branch_id = user_branch_id
            st.write(f"**Chi nhánh:** {branch_mgr.get_branch(user_branch_id)['name']}")

    st.divider()

    # ---- 2. Tải và hiển thị dữ liệu dựa trên vai trò ----

    # ==========================================================
    # GIAO DIỆN DÀNH CHO ADMIN (CÓ DỮ LIỆU LỢI NHUẬN)
    # ==========================================================
    if user_role == 'ADMIN':
        with st.spinner("Đang tải báo cáo tài chính chi tiết..."):
            pnl_data = report_mgr.get_profit_and_loss_overview(report_branch_id, time_range_option)
            best_sellers_data = report_mgr.get_best_selling_products(report_branch_id, limit=10, time_range=time_range_option)

        st.subheader("Báo cáo Lợi nhuận Gộp")
        
        if not pnl_data['order_count'] > 0:
            st.warning("Không có dữ liệu trong khoảng thời gian đã chọn.")
        else:
            # Các chỉ số KPI chính
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Tổng Doanh thu", f"{pnl_data['total_revenue']:,.0f} VNĐ")
            kpi2.metric("Tổng Giá vốn", f"{pnl_data['total_cogs']:,.0f} VNĐ")
            kpi3.metric("Lợi nhuận gộp", f"{pnl_data['total_gross_profit']:,.0f} VNĐ", 
                        delta=f"{pnl_data['profit_margin']:.1f}% Margin")
            kpi4.metric("Tổng số đơn hàng", f"{pnl_data['order_count']}")
            
            # Chuẩn bị dữ liệu cho biểu đồ
            df_chart = pnl_data['daily_data_df'].copy()
            df_chart.reset_index(inplace=True)
            df_chart.rename(columns={'index': 'Ngày'}, inplace=True)
            
            # Biến đổi từ wide-format sang long-format
            df_long = df_chart.melt('Ngày', var_name='Chỉ số', value_name='Giá trị')
            df_long['Chỉ số'] = df_long['Chỉ số'].map({'revenue':'Doanh thu', 'cogs':'Giá vốn', 'profit':'Lợi nhuận'}).fillna(df_long['Chỉ số'])


            # Vẽ biểu đồ bằng Altair
            chart = alt.Chart(df_long[df_long['Chỉ số'].isin(['Doanh thu', 'Giá vốn', 'Lợi nhuận'])]).mark_line(point=True).encode(
                x=alt.X('Ngày:T', title='Ngày'),
                y=alt.Y('Giá trị:Q', title='Số tiền (VNĐ)'),
                color=alt.Color('Chỉ số:N', title='Chỉ số', 
                                scale=alt.Scale(domain=['Doanh thu', 'Giá vốn', 'Lợi nhuận'],
                                                range=['#1f77b4', '#ff7f0e', '#2ca02c'])),
                tooltip=['Ngày', 'Chỉ số', alt.Tooltip('Giá trị:Q', format=',.0f')]
            ).interactive()

            st.altair_chart(chart, use_container_width=True)

    # ==========================================================
    # GIAO DIỆN DÀNH CHO STAFF (CHỈ DOANH THU)
    # ==========================================================
    else:
        with st.spinner("Đang tải báo cáo doanh thu..."):
            revenue_data = report_mgr.get_revenue_overview(report_branch_id, time_range_option)
            best_sellers_data = report_mgr.get_best_selling_products(report_branch_id, limit=10, time_range=time_range_option)

        st.subheader("Tổng quan Doanh thu")
        if not revenue_data['order_count'] > 0:
            st.warning("Không có dữ liệu doanh thu trong khoảng thời gian đã chọn.")
        else:
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Tổng doanh thu", f"{revenue_data['total_revenue']:,.0f} VNĐ")
            kpi2.metric("Tổng số đơn hàng", f"{revenue_data['order_count']}")
            avg_revenue = revenue_data['total_revenue'] / revenue_data['order_count'] if revenue_data['order_count'] > 0 else 0
            kpi3.metric("Doanh thu trung bình/đơn", f"{avg_revenue:,.0f} VNĐ")

            # Biểu đồ doanh thu theo ngày
            if not revenue_data['daily_revenue_df'].empty:
                st.line_chart(revenue_data['daily_revenue_df'].set_index('date'))

    # ---- Báo cáo chung cho tất cả các vai trò ----
    st.divider()
    st.subheader("Top 10 Sản phẩm bán chạy")
    if not best_sellers_data:
        st.warning("Không có dữ liệu về sản phẩm bán chạy.")
    else:
        bestseller_df = pd.DataFrame(best_sellers_data)
        bestseller_df.columns = ["SKU", "Tên Sản phẩm", "Số lượng đã bán"]
        st.dataframe(bestseller_df, use_container_width=True, hide_index=True)
