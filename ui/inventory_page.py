
import streamlit as st
import pandas as pd
from datetime import datetime

# Import managers
from managers.inventory_manager import InventoryManager
from managers.branch_manager import BranchManager
from managers.product_manager import ProductManager
from managers.auth_manager import AuthManager

def render_inventory_page(inv_mgr: InventoryManager, branch_mgr: BranchManager, prod_mgr: ProductManager, auth_mgr: AuthManager):
    st.header("📦 Quản lý Kho")

    user_info = auth_mgr.get_current_user_info()
    if not user_info:
        st.error("Vui lòng đăng nhập.")
        return

    # --- LOGIC PHÂN QUYỀN ---

    user_role = user_info.get('role', 'staff')
    if user_role not in ['admin', 'manager']:
        st.warning("Bạn không có quyền truy cập vào chức năng này.")
        return

    user_branches = user_info.get('branch_ids', [])
    all_branches_list = branch_mgr.get_branches()
    all_branches_map = {b['id']: b['name'] for b in all_branches_list}
    
    allowed_branches_map = {}
    if user_role == 'admin':
        allowed_branches_map = all_branches_map
    else: # manager
        allowed_branches_map = {branch_id: all_branches_map[branch_id] for branch_id in user_branches if branch_id in all_branches_map}

    if not allowed_branches_map:
        st.warning("Tài khoản của bạn chưa được gán vào chi nhánh nào. Vui lòng liên hệ Admin.")
        return

    product_list = prod_mgr.list_products()
    product_map = {p['sku']: p for p in product_list}
    product_sku_list = [p['sku'] for p in product_list]

    tab1, tab2, tab3, tab4 = st.tabs([
        "🚚 Luân chuyển hàng hóa",
        "📥 Nhập kho (từ NCC)",
        "📤 Xuất/Hủy kho",
        "📋 Kiểm kê kho"
    ])

    # --- TAB 1: LUÂN CHUYỂN HÀNG HÓA ---

    with tab1:
        st.subheader("Tạo Phiếu Chuyển Kho")
        with st.form("stock_transfer_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                branch_from_id = st.selectbox(
                    "Từ Chi nhánh",
                    options=list(allowed_branches_map.keys()),
                    format_func=lambda x: allowed_branches_map[x],
                    key="transfer_from"
                )
            with col2:
                # Lọc chi nhánh nhận không được trùng chi nhánh gửi
                available_to_branches = {k: v for k, v in all_branches_map.items() if k != branch_from_id}
                branch_to_id = st.selectbox(
                    "Đến Chi nhánh",
                    options=list(available_to_branches.keys()),
                    format_func=lambda x: available_to_branches[x],
                    key="transfer_to"
                )

            st.write("Thêm sản phẩm cần chuyển:")
            
            # Sử dụng st.data_editor để thêm sản phẩm
            if 'transfer_items' not in st.session_state:
                st.session_state.transfer_items = pd.DataFrame([{"SKU": None, "Số lượng": 1}])

            edited_df = st.data_editor(
                st.session_state.transfer_items,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "SKU": st.column_config.SelectboxColumn(
                        "SKU",
                        help="Chọn mã sản phẩm (SKU)",
                        options=product_sku_list,
                        required=True
                    ),
                    "Số lượng": st.column_config.NumberColumn(
                        "Số lượng",
                        min_value=1,
                        step=1,
                        required=True
                    )
                }
            )

            notes = st.text_area("Ghi chú")
            
            submitted = st.form_submit_button("Tạo Phiếu")
            if submitted:
                # Validate dữ liệu
                if branch_from_id == branch_to_id:
                    st.error("Chi nhánh gửi và nhận không được trùng nhau.")
                elif edited_df.isnull().values.any():
                    st.error("Vui lòng điền đầy đủ thông tin SKU và số lượng.")
                else:
                    items_to_transfer = edited_df.to_dict('records')
                    try:
                        # Gọi hàm manager để tạo phiếu (sẽ được implement sau)
                        inv_mgr.create_stock_transfer(
                            branch_from_id, 
                            branch_to_id, 
                            items_to_transfer, 
                            user_info['uid'], 
                            notes
                        )
                        st.success(f"Đã tạo phiếu chuyển kho từ '{allowed_branches_map[branch_from_id]}' đến '{all_branches_map[branch_to_id]}' thành công!")
                        # Reset dataframe
                        st.session_state.transfer_items = pd.DataFrame([{"SKU": None, "Số lượng": 1}])
                    except Exception as e:
                        st.error(f"Lỗi khi tạo phiếu: {e}")

        st.divider()

        st.subheader("Các Phiếu Chờ Xác Nhận")
        # Chỉ lấy các phiếu đang chờ mà chi nhánh đích nằm trong quyền của user
        pending_transfers = inv_mgr.get_pending_transfers_to_branches(list(allowed_branches_map.keys()))

        if not pending_transfers:
            st.info("Không có phiếu chuyển kho nào đang chờ xác nhận tại chi nhánh của bạn.")
        else:
            for transfer in pending_transfers:
                transfer_id = transfer['id']
                from_name = all_branches_map.get(transfer['branch_from_id'], "N/A")
                to_name = all_branches_map.get(transfer['branch_to_id'], "N/A")
                
                with st.expander(f"Phiếu #{transfer_id} | Từ: {from_name} | Ngày: {transfer['created_at'][:10]}"):
                    st.write(f"**Ghi chú:** {transfer.get('notes', 'Không có')}")
                    
                    items_df = pd.DataFrame(transfer['items'])
                    # Join với thông tin sản phẩm để hiển thị tên
                    items_df['Tên sản phẩm'] = items_df['SKU'].map(lambda sku: product_map.get(sku, {}).get('name', 'Không rõ'))
                    st.dataframe(items_df[['SKU', 'Tên sản phẩm', 'Số lượng']], use_container_width=True)

                    if st.button("Xác Nhận Đã Nhận Đủ Hàng", key=f"confirm_{transfer_id}"):
                        try:
                            # Gọi hàm manager để xác nhận (sẽ được implement sau)
                            inv_mgr.confirm_stock_transfer(transfer_id, user_info['uid'])
                            st.success(f"Đã xác nhận thành công phiếu #{transfer_id}!")
                            st.experimental_rerun() # Tải lại trang để cập nhật danh sách
                        except Exception as e:
                            st.error(f"Lỗi khi xác nhận: {e}")


    # --- TAB 2: NHẬP KHO ---

    with tab2:
        # Giữ nguyên logic cũ
        st.info("Chức năng đang được phát triển")
        pass

    # --- TAB 3: XUẤT HỦY KHO ---

    with tab3:
        # Giữ nguyên logic cũ
        st.info("Chức năng đang được phát triển")
        pass

    # --- TAB 4: KIỂM KÊ KHO ---

    with tab4:
        # Giữ nguyên logic cũ
        st.info("Chức năng đang được phát triển")
        pass
