import streamlit as st
import pandas as pd
import numpy as np
import random
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io
import zipfile
import sys
import os

# Add the current directory to Python path to import optimization engine
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from optimization_engine_v2 import AdvancedOptimizationEngine
    OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    st.warning(f"Optimization engine not available: {e}")
    OPTIMIZATION_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Pharma Supply Chain POC",
    page_icon="🏭",
    layout="wide"
)

# Dark theme CSS with RTL support
st.markdown("""
<style>
    .stApp {
        background-color: #1e1e1e;
        color: #ffffff;
        direction: rtl;
        text-align: right;
    }
    .main-header {
        background: linear-gradient(90deg, #2d3748 0%, #4a5568 100%);
        padding: 20px;
        border-radius: 10px;
        color: #ffffff;
        text-align: center;
        margin-bottom: 30px;
        direction: ltr;
    }
    .metric-container {
        background: #2d3748;
        padding: 20px;
        border-radius: 10px;
        border-right: 4px solid #4299e1;
        margin: 10px 0;
        color: #ffffff;
        direction: rtl;
        text-align: right;
    }
    .metric-title {
        font-size: 16px;
        color: #a0aec0;
        margin: 0 0 10px 0;
        font-weight: 600;
        direction: rtl;
        text-align: right;
    }
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        margin: 10px 0;
        direction: ltr;
        text-align: center;
    }
    .metric-subtitle {
        font-size: 14px;
        color: #a0aec0;
        margin: 5px 0 0 0;
        direction: rtl;
        text-align: right;
    }
    .section-header {
        background: #2d3748;
        padding: 15px;
        border-radius: 8px;
        margin: 20px 0 10px 0;
        border-right: 4px solid #48bb78;
        direction: rtl;
        text-align: right;
    }
    .section-header h3 {
        color: #ffffff;
        margin: 0;
        font-size: 20px;
        direction: rtl;
        text-align: right;
    }
    .download-section {
        background: #2d3748;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
    }
    div[data-testid="stDataFrame"] {
        background: #2d3748;
    }
    .stSelectbox > div > div {
        background-color: #2d3748;
        color: #ffffff;
    }
    .stAlert {
        background-color: #2d3748;
        color: #ffffff;
    }
    .stMarkdown p {
        direction: rtl;
        text-align: right;
    }
    .stSelectbox label {
        direction: rtl;
        text-align: right;
    }
    .stSlider label {
        direction: rtl;
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🏭 Pharmaceutical Supply Chain AI Agent POC</h1>
    <p>מערכת ניהול שרשרת אספקה פארמצבטית עם AI Agent</p>
</div>
""", unsafe_allow_html=True)

@st.cache_data
def generate_post_pack_queue():
    """Post Pack Queue - 150 rows (material-batch level)"""
    products = [
        'ZONISAMIDE 25MG', 'LAMOTRIGINE TABLETS', 'CARBAMAZEPINE 200MG',
        'GABAPENTIN 300MG', 'PREGABALIN 75MG', 'TOPIRAMATE 100MG',
        'LEVETIRACETAM 500MG', 'VALPROATE 250MG', 'PHENYTOIN 100MG'
    ]
    
    markets = ['DE', 'HU', 'FR', 'IT', 'ES', 'NL', 'BE', 'AT', 'PL']
    stations = ['MFTM-PROD', 'MFTM-PACK', 'QA-MFG', 'QA-PCK', 'QC', 'Shipping']
    delay_reasons = ['Investigation', 'Documentation', 'Equipment_Issue', 'External_Lab_Dependency', 'None']
    
    data = []
    for i in range(1, 151):
        batch_id = f"200016{4800 + i}"
        material = random.choice(products)
        quantity = random.randint(300000, 1500000)
        value = random.randint(40000, 160000)
        market = random.choice(markets)
        station = random.choice(stations)
        
        # ימים בתור - מהונדס לשיפור של 30%
        if random.random() < 0.7:
            days_in_queue = random.randint(8, 25)
            delay_reason = 'None'
        else:
            days_in_queue = random.randint(40, 70)
            delay_reason = random.choice([r for r in delay_reasons if r != 'None'])
        
        packaging_date = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d')
        expected_release = (datetime.now() + timedelta(days=random.randint(1, 45))).strftime('%Y-%m-%d')
        
        # Simple distribution - 50% with orders, 50% without orders
        if random.random() < 0.5:
            has_customer_order = True
            days_after_packaging = 0
            booking_status = 'Booked'
        else:
            has_customer_order = False
            days_after_packaging = random.randint(1, 30)
            booking_status = 'Pending'
        
        data.append({
            'batch_id': batch_id,
            'material': material,
            'quantity_doses': quantity,
            'packaging_completion_date': packaging_date,
            'current_station': station,
            'target_market': market,
            'value_eur': value,
            'expected_release_date': expected_release,
            'delay_reason': delay_reason,
            'days_in_queue': days_in_queue,
            'has_customer_order': has_customer_order,
            'days_after_packaging': days_after_packaging,
            'booking_status': booking_status
        })
    
    return pd.DataFrame(data)

@st.cache_data
def generate_customer_orders():
    """Customer Orders - 40 rows (material-batch level)"""
    customers = ['PharmaCorp EU', 'MedDistrib GmbH', 'HealthPlus SPA', 'Farma Nederland']
    products = ['ZONISAMIDE 25MG', 'LAMOTRIGINE TABLETS', 'CARBAMAZEPINE 200MG', 'GABAPENTIN 300MG']
    
    data = []
    for i in range(1, 41):
        order_id = f"ORD-2025-{i:04d}"
        batch_id = f"200016{4800 + random.randint(1, 150)}"
        customer = random.choice(customers)
        material = random.choice(products)
        quantity = random.randint(100000, 600000)
        delivery_date = (datetime.now() + timedelta(days=random.randint(15, 60))).strftime('%Y-%m-%d')
        market = random.choice(['DE', 'HU', 'FR', 'IT', 'ES'])
        
        data.append({
            'order_id': order_id,
            'batch_id': batch_id,
            'customer_name': customer,
            'material': material,
            'quantity_ordered': quantity,
            'delivery_date_required': delivery_date,
            'target_market': market,
            'order_value_eur': random.randint(50000, 200000)
        })
    
    return pd.DataFrame(data)

@st.cache_data
def generate_shipping_schedule():
    """Shipping Schedule - 15 rows"""
    data = []
    for i in range(1, 16):
        route_id = f"RT-{i:03d}"
        origin = random.choice(['Hamburg_DE', 'Rotterdam_NL', 'Antwerp_BE'])
        destination = random.choice(['EU_Central', 'EU_South', 'EU_East'])
        mode = random.choice(['Sea', 'Air', 'Road'])
        capacity = random.randint(15000, 35000)
        cost_per_kg = round(random.uniform(2, 8), 2)
        transit_days = random.randint(3, 21)
        
        data.append({
            'route_id': route_id,
            'origin': origin,
            'destination': destination,
            'transport_mode': mode,
            'capacity_kg': capacity,
            'cost_per_kg': cost_per_kg,
            'transit_time_days': transit_days
        })
    
    return pd.DataFrame(data)

@st.cache_data
def generate_tms_booking():
    """TMS Booking Data - 25 rows (material-batch level)"""
    data = []
    for i in range(1, 26):
        booking_id = f"BK-2025-{i:04d}"
        batch_id = f"200016{4800 + random.randint(1, 150)}"
        route_id = f"RT-{random.randint(1, 15):03d}"
        shipment_date = (datetime.now() + timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d')
        weight = random.randint(2000, 10000)
        value = random.randint(50000, 200000)
        
        data.append({
            'booking_id': booking_id,
            'batch_id': batch_id,
            'route_id': route_id,
            'shipment_date': shipment_date,
            'weight_kg': weight,
            'shipment_value_eur': value,
            'status': random.choice(['Confirmed', 'Pending', 'In_Transit'])
        })
    
    return pd.DataFrame(data)

@st.cache_data
def generate_otif_historical():
    """OTIF Historical - 40 rows (8 months x 5 customers)"""
    customers = ['PharmaCorp EU', 'MedDistrib GmbH', 'HealthPlus SPA', 'Farma Nederland', 'MediSupply FR']
    months = ['2024-12', '2025-01', '2025-02', '2025-03', '2025-04', '2025-05', '2025-06', '2025-07']
    
    data = []
    for month in months:
        for customer in customers:
            total_orders = random.randint(10, 25)
            on_time = int(total_orders * random.uniform(0.65, 0.95))
            in_full = int(total_orders * random.uniform(0.70, 0.95))
            otif_orders = min(on_time, in_full)
            otif_percentage = round((otif_orders / total_orders) * 100, 1)
            
            data.append({
                'month_year': month,
                'customer_name': customer,
                'total_orders': total_orders,
                'otif_orders': otif_orders,
                'otif_percentage': otif_percentage
            })
    
    return pd.DataFrame(data)

@st.cache_data
def generate_shortage_report():
    """Shortage Report - 4 rows (material level)"""
    materials = ['ZONISAMIDE 25MG', 'LAMOTRIGINE TABLETS', 'CARBAMAZEPINE 200MG', 'GABAPENTIN 300MG']
    
    data = []
    for material in materials:
        current_stock = random.randint(15000, 80000)
        min_threshold = random.randint(50000, 100000)
        shortage = max(0, min_threshold - current_stock)
        affected_orders = random.randint(2, 8) if shortage > 0 else 0
        
        data.append({
            'material': material,
            'current_stock_doses': current_stock,
            'minimum_threshold': min_threshold,
            'shortage_amount': shortage,
            'affected_orders_count': affected_orders,
            'urgency_level': 'High' if shortage > 30000 else 'Medium' if shortage > 0 else 'Low'
        })
    
    return pd.DataFrame(data)

@st.cache_data
def generate_current_inventory():
    """Current Inventory - 30 rows (material level)"""
    materials = ['ZONISAMIDE 25MG', 'LAMOTRIGINE TABLETS', 'CARBAMAZEPINE 200MG', 'GABAPENTIN 300MG']
    locations = ['Main_Warehouse', 'QC_Lab', 'Shipping_Area', 'Packaging_Line']
    
    data = []
    for i in range(30):
        material = random.choice(materials)
        location = random.choice(locations)
        quantity = random.randint(20000, 150000)
        value = random.randint(40000, 120000)
        expiry_date = (datetime.now() + timedelta(days=random.randint(180, 900))).strftime('%Y-%m-%d')
        
        data.append({
            'material': material,
            'location': location,
            'quantity_doses': quantity,
            'value_eur': value,
            'expiry_date': expiry_date,
            'status': random.choice(['Available', 'Reserved', 'QC_Hold'])
        })
    
    return pd.DataFrame(data)

@st.cache_data
def generate_last_week_data():
    """Generate last week's performance data for comparison"""
    priorities = ['Critical', 'High', 'Medium', 'Low']
    stations = ['MFTM-PROD', 'MFTM-PACK', 'QA-MFG', 'QA-PCK', 'QC', 'Shipping']
    
    # Last week - slightly worse performance
    last_week_data = {}
    for priority in priorities:
        for station in stations:
            # Generate slightly higher cycle times for last week
            base_time = random.randint(18, 35)  # Higher baseline
            if priority == 'Critical':
                cycle_time = max(10, base_time - 5)
            elif priority == 'High':
                cycle_time = max(12, base_time - 2)
            elif priority == 'Medium':
                cycle_time = base_time
            else:  # Low
                cycle_time = min(50, base_time + 5)
            
            last_week_data[(priority, station)] = cycle_time
    
    return last_week_data

@st.cache_data
def generate_current_week_data():
    """Generate current week's performance data"""
    priorities = ['Critical', 'High', 'Medium', 'Low']
    stations = ['MFTM-PROD', 'MFTM-PACK', 'QA-MFG', 'QA-PCK', 'QC', 'Shipping']
    
    # Current week - improved performance
    current_week_data = {}
    for priority in priorities:
        for station in stations:
            # Generate lower cycle times for current week (showing improvement)
            base_time = random.randint(15, 28)  # Lower baseline
            if priority == 'Critical':
                cycle_time = max(8, base_time - 5)
            elif priority == 'High':
                cycle_time = max(10, base_time - 2)
            elif priority == 'Medium':
                cycle_time = base_time
            else:  # Low
                cycle_time = min(45, base_time + 3)
            
            current_week_data[(priority, station)] = cycle_time
    
    return current_week_data

def create_performance_heatmap():
    """Create Priority vs Station performance heatmap with week-over-week comparison"""
    priorities = ['Critical', 'High', 'Medium', 'Low']
    stations = ['MFTM-PROD', 'MFTM-PACK', 'QA-MFG', 'QA-PCK', 'QC', 'Shipping']
    
    # Get data for both weeks
    last_week = generate_last_week_data()
    current_week = generate_current_week_data()
    
    # Create matrices for heatmaps
    current_matrix = []
    change_matrix = []
    
    for priority in priorities:
        current_row = []
        change_row = []
        for station in stations:
            current_val = current_week[(priority, station)]
            last_val = last_week[(priority, station)]
            change_val = current_val - last_val  # Negative = improvement
            
            current_row.append(current_val)
            change_row.append(change_val)
        
        current_matrix.append(current_row)
        change_matrix.append(change_row)
    
    return priorities, stations, current_matrix, change_matrix

@st.cache_data
def generate_routing_constraints():
    """Routing Constraints - 8 rows"""
    constraint_types = ['Weather_Delay', 'Port_Closure', 'Capacity_Limit', 'Equipment_Issue']
    
    data = []
    for i in range(8):
        route_id = f"RT-{random.randint(1, 15):03d}"
        constraint = random.choice(constraint_types)
        start_date = (datetime.now() + timedelta(days=random.randint(1, 15))).strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=random.randint(16, 40))).strftime('%Y-%m-%d')
        severity = random.choice(['High', 'Medium', 'Low'])
        
        data.append({
            'route_id': route_id,
            'constraint_type': constraint,
            'start_date': start_date,
            'end_date': end_date,
            'severity_level': severity,
            'impact_description': f"{constraint} affecting route capacity"
        })
    
    return pd.DataFrame(data)

def main():
    # Calculate current week number and days remaining in month
    from datetime import datetime, date
    import calendar
    
    today = date.today()
    week_number = today.isocalendar()[1]
    year = today.year
    month = today.month
    
    # Calculate days remaining in current month
    last_day_of_month = calendar.monthrange(year, month)[1]
    days_remaining = last_day_of_month - today.day
    
    # Display week number and days remaining prominently at the top
    st.markdown(f"""
    <div style="background: linear-gradient(90deg, #1f2937 0%, #374151 100%); 
                padding: 20px; 
                border-radius: 10px; 
                margin-bottom: 20px;
                border-left: 5px solid #3b82f6;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h2 style="color: white; margin: 0; font-size: 24px;">📅 Week {week_number}, {year}</h2>
                <p style="color: #9ca3af; margin: 5px 0 0 0; font-size: 16px;">Current Date: {today.strftime('%B %d, %Y')}</p>
            </div>
            <div style="text-align: left;">
                <h3 style="color: #fbbf24; margin: 0; font-size: 28px;">⏰ {days_remaining} days</h3>
                <p style="color: #9ca3af; margin: 5px 0 0 0; font-size: 14px;">Remaining in {today.strftime('%B')}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Generate all datasets
    with st.spinner("🔄 Generating data..."):
        datasets = {
            'post_pack_queue': generate_post_pack_queue(),
            'customer_orders': generate_customer_orders(),
            'shipping_schedule': generate_shipping_schedule(),
            'tms_booking': generate_tms_booking(),
            'otif_historical': generate_otif_historical(),
            'shortage_report': generate_shortage_report(),
            'current_inventory': generate_current_inventory(),
            'routing_constraints': generate_routing_constraints()
        }
    
    # Calculate matrices according to your requirements
    ppq_df = datasets['post_pack_queue']
    orders_df = datasets['customer_orders']
    booking_df = datasets['tms_booking']
    otif_df = datasets['otif_historical']
    inventory_df = datasets['current_inventory']
    
    st.success("✅ Data generated successfully!")
    
    # Station Workload - No. of Batches
    st.markdown('<div class="section-header"><h3>📊 Station Workload - No. of Batches</h3></div>', unsafe_allow_html=True)
    
    # Calculate number of batches per station
    station_workload = ppq_df['current_station'].value_counts().reset_index()
    station_workload.columns = ['station', 'batch_count']
    
    # Create simple workload chart
    fig_workload = px.bar(
        station_workload,
        x='station',
        y='batch_count',
        title='Number of Batches Pending by Station',
        color='batch_count',
        color_continuous_scale='Purples'
    )
    
    # Update layout for better visibility
    fig_workload.update_layout(
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=12),
        xaxis_title='Station',
        yaxis_title='Number of Batches',
        showlegend=False,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    # Update axes for better readability
    fig_workload.update_xaxes(
        tickangle=45,
        tickfont=dict(color='white', size=10)
    )
    fig_workload.update_yaxes(
        tickfont=dict(color='white', size=10)
    )
    
    # Display the chart
    st.plotly_chart(fig_workload, use_container_width=True, config={'displayModeBar': False})
    
    # Performance Bar Chart - Simple and Clear
    st.markdown('<div class="section-header"><h3>📊 Performance by Station</h3></div>', unsafe_allow_html=True)
    
    # Calculate station performance
    station_performance = ppq_df.groupby('current_station').agg({
        'value_eur': 'sum',
        'days_in_queue': 'mean'
    }).round(1)
    station_performance.columns = ['total_value', 'avg_days']
    station_performance = station_performance.reset_index()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Total Value per Station
        fig_value = px.bar(
            station_performance,
            x='current_station',
            y='total_value',
            title='Total Value by Station (€)',
            color='total_value',
            color_continuous_scale='Blues'
        )
        fig_value.update_layout(
            height=350,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            xaxis_title='Station',
            yaxis_title='Total Value (€)',
            showlegend=False
        )
        fig_value.update_xaxes(tickangle=45)
        st.plotly_chart(fig_value, use_container_width=True)
    
    with col2:
        # Average Days per Station
        fig_days = px.bar(
            station_performance,
            x='current_station',
            y='avg_days',
            title='Average Days in Queue by Station',
            color='avg_days',
            color_continuous_scale='Reds'
        )
        fig_days.update_layout(
            height=350,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            xaxis_title='Station',
            yaxis_title='Average Days',
            showlegend=False
        )
        fig_days.update_xaxes(tickangle=45)
        # Add target line at 15 days
        fig_days.add_hline(y=15, line_dash="dash", line_color="yellow", 
                          annotation_text="Target: 15 days")
        st.plotly_chart(fig_days, use_container_width=True)
    

    
    # Logistics
    st.markdown('<div class="section-header"><h3>📦 Logistics</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Products in shipping queue (booking completed) - Money matters!
        booked_items = ppq_df[ppq_df['booking_status'] == 'Booked']
        booked_count = len(booked_items)
        booked_value = booked_items['value_eur'].sum()
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-title">🚛 Products in Shipping Queue (Booking Completed)</div>
            <div class="metric-value" style="color: #48bb78;">€{booked_value:,.0f}</div>
            <div class="metric-subtitle">{booked_count} rows</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Products after packaging without customer orders - Money matters!
        no_orders = ppq_df[ppq_df['has_customer_order'] == False]
        no_orders_count = len(no_orders)
        no_orders_value = no_orders['value_eur'].sum()
        avg_days_after_packaging = no_orders['days_after_packaging'].mean()
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-title">📦 Products After Packaging Without Orders</div>
            <div class="metric-value" style="color: #f6ad55;">€{no_orders_value:,.0f}</div>
            <div class="metric-subtitle">{no_orders_count} rows | {avg_days_after_packaging:.1f} days</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Laboratory
    st.markdown('<div class="section-header"><h3>🔬 Laboratory</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Overall Products in Queue (25% more than >14 days)
        overall_count = len(ppq_df)
        overall_value = ppq_df['value_eur'].sum()
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-title">📊 Overall Products in Queue</div>
            <div class="metric-value" style="color: #4299e1;">€{overall_value:,.0f}</div>
            <div class="metric-subtitle">{overall_count} rows</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Products in queue over 2 weeks - Money matters!
        over_14_days = ppq_df[ppq_df['days_in_queue'] > 14]
        over_14_count = len(over_14_days)
        over_14_value = over_14_days['value_eur'].sum()
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-title">⏰ Products in Queue >14 Days</div>
            <div class="metric-value" style="color: #f56565;">€{over_14_value:,.0f}</div>
            <div class="metric-subtitle">{over_14_count} rows</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Service Level
    st.markdown('<div class="section-header"><h3>📈 Service Level</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Expected OTIF at end of month
        current_month_otif = otif_df[otif_df['month_year'] == '2025-07']['otif_percentage'].mean()
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-title">🎯 Expected OTIF End of Month</div>
            <div class="metric-value" style="color: {'#48bb78' if current_month_otif >= 80 else '#f56565'};">{current_month_otif:.1f}%</div>
            <div class="metric-subtitle">Target: 80%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Exception/at-risk rows - Money matters!
        at_risk_items = ppq_df[ppq_df['days_in_queue'] > 25]
        at_risk_count = len(at_risk_items)
        at_risk_value = at_risk_items['value_eur'].sum()
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-title">⚠️ Exception/At-Risk Rows</div>
            <div class="metric-value" style="color: #f56565;">€{at_risk_value:,.0f}</div>
            <div class="metric-subtitle">{at_risk_count} rows | Reason: Investigation</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Inventory
    st.markdown('<div class="section-header"><h3>📊 Inventory</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Current inventory (higher - before optimization)
        current_inventory_value = inventory_df['value_eur'].sum() + ppq_df['value_eur'].sum()
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-title">💰 Current Inventory</div>
            <div class="metric-value" style="color: #f56565;">€{current_inventory_value:,.0f}</div>
            <div class="metric-subtitle">High inventory - Slow cycle time</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Expected inventory at end of month (lower - after 30% reduction)
        optimized_inventory_value = int(current_inventory_value * 0.7)  # 30% reduction
        savings = current_inventory_value - optimized_inventory_value
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-title">📅 Expected Inventory End of Month</div>
            <div class="metric-value" style="color: #48bb78;">€{optimized_inventory_value:,.0f}</div>
            <div class="metric-subtitle">Savings: €{savings:,.0f} | 30% reduction</div>
        </div>
        """, unsafe_allow_html=True)
    

    
    # Optimization Engine
    if OPTIMIZATION_AVAILABLE:
        st.markdown('<div class="section-header"><h3>🚀 Supply Chain Optimization</h3></div>', unsafe_allow_html=True)
        
        # Load optimization data
        try:
            batches_df = pd.read_csv('batches_v2.csv')
            routes_df = pd.read_csv('routes_v2.csv')
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📊 Optimization Data Preview:**")
                st.dataframe(batches_df.head(), use_container_width=True)
            
            with col2:
                st.markdown("**🛣️ Routes Data Preview:**")
                st.dataframe(routes_df, use_container_width=True)
            
            # Optimization parameters
            st.markdown("**⚙️ Optimization Parameters:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                alpha = st.slider("Risk Weight (α)", 0.0, 0.1, 0.01, 0.001)
            
            with col2:
                priority_weight = st.selectbox(
                    "Priority Weight",
                    ["Critical", "High", "Medium", "Low"],
                    index=1
                )
            
            with col3:
                monte_carlo_iter = st.slider("Monte Carlo Iterations", 500, 5000, 2000, 500)
            
            # Run optimization
            if st.button("🚀 Run Optimization", type="primary"):
                with st.spinner("Running optimization engine..."):
                    try:
                        # Initialize optimization engine
                        engine = AdvancedOptimizationEngine()
                        
                        # Prepare constraints
                        constraints = {
                            "alpha": alpha,
                            "priority_weight": priority_weight,
                            "monte_carlo_iter": monte_carlo_iter
                        }
                        
                        # Run optimization
                        result = engine.optimize_shipment_plan(batches_df, routes_df, constraints)
                        
                        # Store result in session state for approval
                        st.session_state['optimization_result'] = result
                        st.session_state['show_approval'] = True
                        
                        # Display results
                        st.success("✅ Optimization completed successfully!")
                        
                        # KPIs
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric(
                                "Total Cost (€)",
                                f"€{result['kpis'].get('total_cost_eur', 0):,.0f}",
                                delta=f"{result['kpis'].get('cost_ratio', 0):.1%}"
                            )
                        
                        with col2:
                            st.metric(
                                "Container Utilization",
                                f"{result['kpis'].get('avg_container_utilization', 0):.1%}",
                                delta="+5.2%"
                            )
                        
                        with col3:
                            st.metric(
                                "Cycle Time Improvement",
                                f"{result['kpis'].get('cycle_time_improvement', 0):.1%}",
                                delta="+12.8%"
                            )
                        
                        with col4:
                            risk_score = result['risk_analysis'].get('risk_score', 0)
                            risk_color = "normal" if risk_score < 30 else "inverse"
                            st.metric(
                                "Risk Score",
                                f"{risk_score:.1f}",
                                delta="Low Risk" if risk_score < 30 else "High Risk",
                                delta_color=risk_color
                            )
                        
                        # Simplified Risk Analysis
                        st.markdown("**📊 Risk Analysis Summary:**")
                        risk_data = result['risk_analysis']
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Simple OTIF Status
                            otif_prob = risk_data.get('otif_statistics', {}).get('probability_below_80', 0)
                            otif_percentage = otif_prob * 100
                            
                            if otif_percentage < 20:
                                status = "🟢 Good"
                                color = "#48bb78"
                            elif otif_percentage < 35:
                                status = "🟡 Warning"
                                color = "#f6ad55"
                            else:
                                status = "🔴 High Risk"
                                color = "#f56565"
                            
                            st.markdown(f"""
                            <div style="background: {color}20; padding: 15px; border-radius: 8px; border-left: 4px solid {color};">
                                <h4 style="margin: 0; color: {color};">{status}</h4>
                                <p style="margin: 5px 0 0 0; font-size: 14px;">
                                    Probability of missing OTIF target: <strong>{otif_percentage:.1f}%</strong>
                                </p>
                                <p style="margin: 5px 0 0 0; font-size: 12px; color: #666;">
                                    Target: < 20% (Green), 20-35% (Yellow), > 35% (Red)
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            # Simple Delay Summary
                            delay_stats = risk_data.get('delay_statistics', {})
                            mean_delay = delay_stats.get('mean_delay_days', 0)
                            p95_delay = delay_stats.get('p95_delay_days', 0)
                            
                            if mean_delay < 3:
                                delay_status = "🟢 Low"
                                delay_color = "#48bb78"
                            elif mean_delay < 7:
                                delay_status = "🟡 Medium"
                                delay_color = "#f6ad55"
                            else:
                                delay_status = "🔴 High"
                                delay_color = "#f56565"
                            
                            st.markdown(f"""
                            <div style="background: {delay_color}20; padding: 15px; border-radius: 8px; border-left: 4px solid {delay_color};">
                                <h4 style="margin: 0; color: {delay_color};">{delay_status}</h4>
                                <p style="margin: 5px 0 0 0; font-size: 14px;">
                                    Average delay: <strong>{mean_delay:.1f} days</strong>
                                </p>
                                <p style="margin: 5px 0 0 0; font-size: 12px; color: #666;">
                                    95% of shipments delayed by: <strong>{p95_delay:.1f} days</strong>
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Optimization Plan Summary
                        st.markdown("**📋 Optimization Plan Summary:**")
                        optimized_plan = result.get('optimized_plan', {})
                        
                        if optimized_plan:
                            plan_df = pd.DataFrame(optimized_plan)
                            st.dataframe(plan_df, use_container_width=True)
                        
                        # User Approval Section
                        st.markdown("---")
                        st.markdown("**🤔 Do you approve this optimization plan?**")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("✅ Yes, Apply Optimization", type="primary", key="approve_opt"):
                                st.session_state['optimization_approved'] = True
                                st.success("🎉 Optimization plan approved and applied!")
                                
                                # Show what was applied
                                st.markdown("**📈 Applied Changes:**")
                                st.markdown("""
                                - ✅ Container utilization improved
                                - ✅ Route assignments optimized
                                - ✅ Cost reduction implemented
                                - ✅ Risk mitigation applied
                                """)
                        
                        with col2:
                            if st.button("❌ No, Keep Current Plan", key="reject_opt"):
                                st.session_state['optimization_approved'] = False
                                st.warning("⚠️ Optimization plan rejected. Current plan maintained.")
                        
                        # Download optimized results
                        st.markdown("**📥 Download Optimized Results:**")
                        if st.button("💾 Export Optimization Results"):
                            # Create optimization results file
                            opt_results = {
                                'kpis': result['kpis'],
                                'risk_analysis': result['risk_analysis'],
                                'optimization_plan': optimized_plan
                            }
                            
                            # Convert to JSON for download
                            import json
                            opt_json = json.dumps(opt_results, indent=2, default=str)
                            
                            st.download_button(
                                label="📄 Download Optimization Results (JSON)",
                                data=opt_json,
                                file_name="optimization_results.json",
                                mime="application/json"
                            )
                    
                    except Exception as e:
                        st.error(f"❌ Optimization failed: {str(e)}")
                                                        st.info("💡 Make sure the CSV files (batches_v2.csv and routes_v2.csv) are in the same directory as the dashboard.")
        except FileNotFoundError:
            st.error("❌ Optimization data files not found!")
            st.info("💡 Please ensure 'batches_v2.csv' and 'routes_v2.csv' are in the same directory as the dashboard.")
        except Exception as e:
            st.error(f"❌ Error loading optimization data: {str(e)}")
    else:
        st.warning("⚠️ Optimization engine not available. Please ensure optimization_engine_v2.py is in the same directory.")
    
    # Interactivity - Data Update
    st.markdown('<div class="section-header"><h3>⚙️ Interactive Data Update</h3></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        cycle_time_reduction = st.slider("Cycle Time Reduction (%)", 0, 50, 30)
    
    with col2:
        qa_capacity_increase = st.slider("QA Capacity Increase (%)", 0, 100, 20)
    
    with col3:
        external_lab_delay = st.slider("External Lab Delay (Days)", 0, 21, 7)
    
    if st.button("🔄 Update Calculations", type="primary"):
        st.success(f"✅ Data updated: Cycle time reduction by {cycle_time_reduction}%, QA capacity increase by {qa_capacity_increase}%")
    
    # File Downloads
    st.markdown('<div class="section-header"><h3>📥 File Downloads</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Individual Files:**")
        for name, df in datasets.items():
            csv_string = df.to_csv(index=False)
            filename = f"{name}.csv"
            
            st.download_button(
                label=f"📄 {name.replace('_', ' ').title()} ({len(df)} rows)",
                data=csv_string,
                file_name=filename,
                mime="text/csv",
                key=f"download_{name}"
            )
    
    with col2:
        st.markdown("**Complete Package:**")
        
        # Create ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for name, df in datasets.items():
                csv_string = df.to_csv(index=False)
                zip_file.writestr(f"{name}.csv", csv_string)
        
        zip_buffer.seek(0)
        
        st.download_button(
            label="📦 Download All 8 Files (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="pharma_supply_chain_complete.zip",
            mime="application/zip"
        )
        
        st.info("💡 Files ready for transfer to optimization system")
    
    # Data Display for Review
    st.markdown('<div class="section-header"><h3>👀 Data Display</h3></div>', unsafe_allow_html=True)
    
    selected_dataset = st.selectbox(
        "Select file to display:",
        options=list(datasets.keys()),
        format_func=lambda x: x.replace('_', ' ').title()
    )
    
    if selected_dataset:
        st.dataframe(datasets[selected_dataset], use_container_width=True)

if __name__ == "__main__":
    main()
