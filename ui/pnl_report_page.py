
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
from ui._utils import render_page_title, render_section_header
from utils.formatters import format_currency

def render_pnl_report_page(report_mgr, branch_mgr, auth_mgr):
    render_page_title("📈 Báo cáo Kết quả Kinh doanh (P&L)")
    st.info("Báo cáo này tổng hợp doanh thu, giá vốn và chi phí để tính toán lợi nhuận gộp và lợi nhuận ròng trong một khoảng thời gian tùy chọn.")

    # --- 1. FILTERS ---
    user_info = auth_mgr.get_current_user_info()
    user_role = user_info.get('role', 'staff')
    
    all_branches_map = {b['id']: b['name'] for b in branch_mgr.list_branches()}
    
    branch_options = {}
    if user_role == 'admin':
        branch_options = {'all': "Toàn bộ hệ thống", **all_branches_map}
    else:
        user_branches = user_info.get('branch_ids', [])
        branch_options = {bid: all_branches_map[bid] for bid in user_branches if bid in all_branches_map}

    cols = st.columns([1, 1, 2])
    today = datetime.now()
    start_date = cols[0].date_input("Từ ngày", today - timedelta(days=30))
    end_date = cols[1].date_input("Đến ngày", today)
    selected_branch_key = cols[2].selectbox(
        "Xem báo cáo cho", 
        options=list(branch_options.keys()),
        format_func=lambda k: branch_options[k]
    )

    if st.button("📊 Xem Báo cáo", use_container_width=True):
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        branch_ids_for_query = []
        if selected_branch_key != 'all':
            branch_ids_for_query = [selected_branch_key]

        try:
            with st.spinner("Đang tổng hợp dữ liệu..."):
                pnl_result = report_mgr.get_profit_loss_statement(
                    start_date=start_datetime,
                    end_date=end_datetime,
                    branch_ids=branch_ids_for_query
                )
            
            if not pnl_result or not pnl_result.get("success"):
                st.error("Không thể tạo báo cáo: " + pnl_result.get("message", "Không có dữ liệu."))
                return

            pnl_data = pnl_result.get("data", {})
            if not pnl_data:
                st.warning("Không tìm thấy dữ liệu phù hợp với các bộ lọc đã chọn.")
                return

            st.success(f"Báo cáo cho: **{branch_options[selected_branch_key]}** từ **{start_date}** đến **{end_date}**")
            st.markdown("---")

            # --- 2. DISPLAY METRICS ---
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Tổng Doanh thu", format_currency(pnl_data.get('total_revenue', 0)))
            col2.metric("Tổng Giá vốn (COGS)", format_currency(pnl_data.get('total_cogs', 0)))
            col3.metric("Lợi nhuận gộp", format_currency(pnl_data.get('gross_profit', 0)))
            
            net_profit = pnl_data.get('net_profit', 0)
            net_profit_delta_color = "normal" if net_profit >= 0 else "inverse"
            col4.metric("Lợi nhuận Ròng", format_currency(net_profit), delta_color=net_profit_delta_color)

            st.markdown("---")
            
            # --- 3. DISPLAY CHARTS & DETAILS ---
            render_section_header("Phân tích Chi phí Hoạt động (OPEX)")
            
            total_opex = pnl_data.get('total_operating_expenses', 0)
            if total_opex == 0:
                st.info("Không phát sinh chi phí hoạt động trong kỳ báo cáo.")
            else:
                expenses_by_group = pnl_data.get("operating_expenses_by_group", {})
                if expenses_by_group:
                    df_group = pd.DataFrame(expenses_by_group.items(), columns=['Nhóm chi phí', 'Số tiền'])
                    df_group = df_group[df_group['Số tiền'] > 0]
                    if not df_group.empty:
                        fig_group = px.pie(df_group, values='Số tiền', names='Nhóm chi phí', title='Tỷ trọng Chi phí theo Nhóm')
                        st.plotly_chart(fig_group, use_container_width=True)
                        with st.expander("Xem chi tiết"):
                            st.dataframe(df_group.style.format({'Số tiền': lambda x: format_currency(x)}), use_container_width=True)
                    else:
                        st.info("Không có dữ liệu chi phí để hiển thị.")
                else:
                    st.info("Không có dữ liệu chi tiết về chi phí hoạt động.")

        except Exception as e:
            st.error("Đã xảy ra lỗi khi tạo báo cáo.")
            st.exception(e)
