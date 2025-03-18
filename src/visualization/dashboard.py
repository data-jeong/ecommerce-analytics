import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(
    page_title="E-commerce Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# 데이터 로드
@st.cache_data
def load_data():
    data_dir = Path("data/analysis_results")
    
    return {
        'daily_sales': pd.read_csv(data_dir / "daily_sales.csv"),
        'category_performance': pd.read_csv(data_dir / "category_performance.csv"),
        'customer_segments': pd.read_csv(data_dir / "customer_segments.csv"),
        'seller_performance': pd.read_csv(data_dir / "seller_performance.csv"),
        'rfm_analysis': pd.read_csv(data_dir / "rfm_analysis.csv")
    }

def main():
    # 타이틀
    st.title("E-commerce Analytics Dashboard")
    
    try:
        # 데이터 로드
        data = load_data()
        
        # 탭 생성
        tab1, tab2, tab3, tab4 = st.tabs([
            "Sales Overview", 
            "Product Analysis",
            "Customer Analysis",
            "Seller Analysis"
        ])
        
        # Sales Overview 탭
        with tab1:
            st.header("Sales Overview")
            
            # 일별 매출 추이
            daily_sales = data['daily_sales']
            daily_sales['date'] = pd.to_datetime(daily_sales['date'])
            
            fig_sales = px.line(
                daily_sales,
                x='date',
                y=['total_revenue', 'average_order_value'],
                title='Daily Sales Trend'
            )
            st.plotly_chart(fig_sales, use_container_width=True)
            
            # KPI 지표들
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Total Revenue",
                    f"${daily_sales['total_revenue'].sum():,.2f}",
                    f"{daily_sales['total_revenue'].pct_change().mean():.1%}"
                )
            
            with col2:
                st.metric(
                    "Total Orders",
                    f"{daily_sales['total_orders'].sum():,}",
                    f"{daily_sales['total_orders'].pct_change().mean():.1%}"
                )
            
            with col3:
                st.metric(
                    "Average Order Value",
                    f"${daily_sales['average_order_value'].mean():,.2f}",
                    f"{daily_sales['average_order_value'].pct_change().mean():.1%}"
                )
        
        # Product Analysis 탭
        with tab2:
            st.header("Product Analysis")
            
            # 카테고리별 매출
            category_perf = data['category_performance']
            
            fig_category = px.bar(
                category_perf.head(10),
                x='product_category_name_english',
                y='total_revenue',
                title='Top 10 Categories by Revenue'
            )
            st.plotly_chart(fig_category, use_container_width=True)
            
            # 카테고리별 상세 정보
            st.dataframe(
                category_perf.style.format({
                    'total_revenue': '${:,.2f}',
                    'average_price': '${:,.2f}',
                    'average_shipping_days': '{:,.1f}'
                })
            )
        
        # Customer Analysis 탭
        with tab3:
            st.header("Customer Analysis")
            
            # 고객 세그먼트 분석
            customer_segments = data['customer_segments']
            
            fig_segments = px.treemap(
                customer_segments,
                path=[px.Constant("All"), 'customer_region', 'customer_city_size'],
                values='total_revenue',
                title='Customer Segments by Revenue'
            )
            st.plotly_chart(fig_segments, use_container_width=True)
            
            # RFM 분석
            rfm = data['rfm_analysis']
            
            # RFM 점수 분포
            col1, col2 = st.columns(2)
            
            with col1:
                fig_rfm_dist = px.histogram(
                    rfm,
                    x='RFM_score',
                    title='RFM Score Distribution'
                )
                st.plotly_chart(fig_rfm_dist, use_container_width=True)
            
            with col2:
                fig_rfm_scatter = px.scatter(
                    rfm,
                    x='recency',
                    y='monetary',
                    size='frequency',
                    title='Customer RFM Analysis'
                )
                st.plotly_chart(fig_rfm_scatter, use_container_width=True)
        
        # Seller Analysis 탭
        with tab4:
            st.header("Seller Analysis")
            
            # 판매자 성과 분석
            seller_perf = data['seller_performance']
            
            # 판매자 위치별 매출
            fig_seller_map = px.scatter_mapbox(
                seller_perf,
                lat=0,  # 실제 위도 데이터 필요
                lon=0,  # 실제 경도 데이터 필요
                size='total_revenue',
                color='average_delivery_delay',
                title='Seller Performance by Location'
            )
            fig_seller_map.update_layout(mapbox_style="open-street-map")
            st.plotly_chart(fig_seller_map, use_container_width=True)
            
            # 판매자 성과 상세 정보
            st.dataframe(
                seller_perf.style.format({
                    'total_revenue': '${:,.2f}',
                    'average_delivery_delay': '{:,.1f}'
                })
            )
    
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")

if __name__ == "__main__":
    main() 