from datetime import datetime, timedelta
from google.cloud.firestore import Query
import pandas as pd

class ReportManager:
    def __init__(self, firebase_client):
        self.db = firebase_client.db
        self.orders_collection = self.db.collection('orders')
        self.products_collection = self.db.collection('products')

    def _get_date_range(self, time_range):
        end_date = datetime.now()
        if time_range == '7d':
            start_date = end_date - timedelta(days=7)
        elif time_range == '30d':
            start_date = end_date - timedelta(days=30)
        elif time_range == 'mtd':
            start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif time_range == 'ytd':
            start_date = end_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else: # Default to 7 days
            start_date = end_date - timedelta(days=7)
        return start_date, end_date

    def get_profit_and_loss_overview(self, branch_id=None, time_range='7d'):
        """
        Lấy báo cáo tổng quan Doanh thu, Giá vốn và Lợi nhuận gộp.
        Chức năng này dành cho vai trò ADMIN.
        """
        start_date, end_date = self._get_date_range(time_range)

        query = self.orders_collection
        if branch_id:
            query = query.where('branch_id', '==', branch_id)
        
        query = query.where('created_at', '>=', start_date.isoformat())
        query = query.where('created_at', '<=', end_date.isoformat())

        orders = query.stream()

        daily_data = {}

        for order in orders:
            order_data = order.to_dict()
            order_date_str = datetime.fromisoformat(order_data['created_at']).strftime('%Y-%m-%d')

            if order_date_str not in daily_data:
                daily_data[order_date_str] = {'revenue': 0, 'cogs': 0, 'orders': 0}

            daily_data[order_date_str]['revenue'] += order_data.get('grand_total', 0)
            daily_data[order_date_str]['cogs'] += order_data.get('total_cogs', 0)
            daily_data[order_date_str]['orders'] += 1
        
        # Chuyển đổi sang DataFrame của Pandas để dễ xử lý
        if not daily_data:
            return self._empty_pnl_report(start_date, end_date)

        df = pd.DataFrame.from_dict(daily_data, orient='index')
        df.index = pd.to_datetime(df.index)
        
        # Tạo một dải ngày đầy đủ để đảm bảo không thiếu ngày nào trên biểu đồ
        full_date_range = pd.date_range(start=start_date.date(), end=end_date.date(), freq='D')
        df = df.reindex(full_date_range, fill_value=0)
        df.index.name = 'date'

        df['profit'] = df['revenue'] - df['cogs']

        total_revenue = df['revenue'].sum()
        total_cogs = df['cogs'].sum()
        total_profit = df['profit'].sum()
        total_orders = df['orders'].sum()

        return {
            'total_revenue': total_revenue,
            'total_cogs': total_cogs,
            'total_gross_profit': total_profit,
            'order_count': total_orders,
            'profit_margin': (total_profit / total_revenue) * 100 if total_revenue > 0 else 0,
            'daily_data_df': df,
            'start_date': start_date,
            'end_date': end_date
        }
    
    def _empty_pnl_report(self, start_date, end_date):
        """Trả về một cấu trúc báo cáo rỗng khi không có dữ liệu."""
        return {
            'total_revenue': 0,
            'total_cogs': 0,
            'total_gross_profit': 0,
            'order_count': 0,
            'profit_margin': 0,
            'daily_data_df': pd.DataFrame(columns=['revenue', 'cogs', 'profit', 'orders']),
            'start_date': start_date,
            'end_date': end_date
        }

    def get_revenue_overview(self, branch_id=None, time_range='7d'):
        """
        Lấy tổng quan doanh thu (phiên bản đơn giản cho STAFF).
        """
        start_date, end_date = self._get_date_range(time_range)

        query = self.orders_collection
        if branch_id:
            query = query.where('branch_id', '==', branch_id)
        
        query = query.where('created_at', '>=', start_date.isoformat())
        query = query.where('created_at', '<=', end_date.isoformat())

        orders = query.stream()
        
        daily_revenue = {}
        order_count = 0
        total_revenue = 0

        for order in orders:
            order_data = order.to_dict()
            total_revenue += order_data.get('grand_total', 0) # Sửa lại tên trường
            order_count += 1
            
            order_date_str = datetime.fromisoformat(order_data['created_at']).strftime('%Y-%m-%d')
            daily_revenue[order_date_str] = daily_revenue.get(order_date_str, 0) + order_data.get('grand_total', 0)
        
        df = pd.DataFrame(list(daily_revenue.items()), columns=['date', 'revenue'])
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
        
        return {
            'total_revenue': total_revenue,
            'order_count': order_count,
            'daily_revenue_df': df, # Trả về DataFrame
            'start_date': start_date,
            'end_date': end_date
        }

    def get_best_selling_products(self, branch_id=None, limit=10, time_range='mtd'):
        """Lấy danh sách sản phẩm bán chạy nhất trong một khoảng thời gian."""
        start_date, end_date = self._get_date_range(time_range)

        query = self.orders_collection
        if branch_id:
            query = query.where('branch_id', '==', branch_id)

        query = query.where('created_at', '>=', start_date.isoformat())
        query = query.where('created_at', '<=', end_date.isoformat())

        orders = query.stream()
        
        product_sales = {}
        for order in orders:
            for item in order.to_dict().get('items', []):
                sku = item['sku']
                quantity = item['quantity']
                product_sales[sku] = product_sales.get(sku, 0) + quantity
        
        sorted_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        product_details = []
        for sku, quantity_sold in sorted_products:
            product_doc = self.products_collection.document(sku).get()
            if product_doc.exists:
                product_data = product_doc.to_dict()
                product_details.append({
                    'sku': sku,
                    'name': product_data.get('name', 'N/A'),
                    'quantity_sold': quantity_sold
                })
            else:
                 product_details.append({
                    'sku': sku,
                    'name': f"(Sản phẩm đã bị xóa - {sku})",
                    'quantity_sold': quantity_sold
                })
        
        return product_details
