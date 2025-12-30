import streamlit as st
import pandas as pd
from datetime import date

def render_promotions_page():
    st.title("🎁 Quản lý Khuyến mãi")

    promotion_mgr = st.session_state.promotion_mgr
    product_mgr = st.session_state.product_mgr

    # Initialize session state for simulation results
    if 'simulation_results' not in st.session_state:
        st.session_state.simulation_results = None

    # --- FORM ĐỂ TẠO/MÔ PHỎNG --- 
    with st.form("promo_form"):
        st.header("Tạo hoặc Mô phỏng Chương trình Giá")

        promo_name = st.text_input("Tên chương trình", "Chương trình giảm giá tháng 6", help="VD: Khai trương chi nhánh mới")
        promo_desc = st.text_area("Mô tả", "Giảm giá đặc biệt cho một số mặt hàng tồn kho.")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Ngày bắt đầu", value=date.today())
        with col2:
            end_date = st.date_input("Ngày kết thúc", value=date(date.today().year, 12, 31))

        st.write("**Quy tắc giảm giá:**")
        auto_discount = st.number_input("Giảm giá tự động (%)", 0, 100, 10)
        manual_limit = st.number_input("Giảm thêm thủ công tối đa (%)", 0, 100, 5)
        
        st.write("**Ràng buộc:**")
        min_margin = st.number_input("Biên lợi nhuận tối thiểu (%)", 0, 100, 10)
        
        # --- NÚT HÀNH ĐỘNG ---
        col_btn1, col_btn2, _ = st.columns([1,1,3])
        submitted_simulate = col_btn1.form_submit_button("Mô phỏng Hiệu quả", use_container_width=True)
        submitted_create = col_btn2.form_submit_button("Lưu Chương trình", type="primary", use_container_width=True)

    # --- XỬ LÝ LOGIC BÊN NGOÀI FORM ---
    # Lấy dữ liệu từ form để xử lý
    form_data = {
        "name": promo_name,
        "description": promo_desc,
        "is_active": False,
        "start_datetime": f"{start_date.isoformat()}T00:00:00Z",
        "end_datetime": f"{end_date.isoformat()}T23:59:59Z",
        "priority": 100,
        "stacking_rule": "EXCLUSIVE",
        "promotion_type": "PRICE_PROGRAM",
        "scope": {"type": "ALL", "ids": []},
        "rules": {
            "auto_discount": {"type": "PERCENT", "value": auto_discount},
            "manual_extra_limit": {"type": "PERCENT", "value": manual_limit}
        },
        "constraints": {"min_margin_floor_percent": min_margin}
    }

    if submitted_simulate:
        if not promo_name:
            st.error("Vui lòng nhập Tên chương trình trước khi mô phỏng.")
        else:
            with st.spinner("Đang chạy mô phỏng trên tất cả sản phẩm..."):
                results = promotion_mgr.simulate_price_program_impact(form_data, product_mgr)
                st.session_state.simulation_results = pd.DataFrame(results)
                st.toast("Mô phỏng hoàn tất!")

    if submitted_create:
        if not promo_name:
            st.error("Vui lòng nhập Tên chương trình.")
        else:
            success, message = promotion_mgr.create_promotion(form_data)
            if success:
                st.success(f"✅ Đã lưu thành công chương trình: {promo_name}")
                st.session_state.simulation_results = None # Clear simulation
                st.rerun()
            else:
                st.error(message)

    # --- HIỂN THỊ KẾT QUẢ MÔ PHỎNG ---
    if st.session_state.simulation_results is not None and not st.session_state.simulation_results.empty:
        st.header("Kết quả Mô phỏng")
        df = st.session_state.simulation_results

        # Styling
        def style_rows(row):
            if row.warnings:
                return ['background-color: #FFF0F0'] * len(row)
            return [''] * len(row)

        st.dataframe(
            df.style.apply(style_rows, axis=1).format({
                'cost_price': "{:,.0f}",
                'original_price': "{:,.0f}",
                'original_margin_percent': "{:.1f}%",
                'price_after_auto': "{:,.0f}",
                'auto_margin_percent': "{:.1f}%",
                'price_after_manual_max': "{:,.0f}",
                'manual_max_margin_percent': "{:.1f}%",
            }),
            use_container_width=True
        )
        st.info(f"Tìm thấy {len(df[df.warnings.str.len() > 0])} sản phẩm có cảnh báo về lợi nhuận.")


    # --- HIỂN THỊ CÁC CHƯƠNG TRÌNH ĐÃ CÓ ---
    st.header("Chương trình Đã Lưu")
    promotions = promotion_mgr.collection_ref.order_by("name").get()
    if not promotions:
        st.info("Chưa có chương trình khuyến mãi nào được lưu.")
    else:
        for promo in promotions:
            promo_data = promo.to_dict()
            with st.expander(f"{promo_data.get('name', 'N/A')} - [Trạng thái: {'Hoạt động' if promo_data.get('is_active') else 'Không hoạt động'}]"):
                st.json(promo_data)
