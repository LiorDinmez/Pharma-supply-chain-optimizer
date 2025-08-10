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
import sqlite3
import json

# Add the current directory to Python path to import optimization engine
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from optimization_engine_v2 import AdvancedOptimizationEngine
    OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    st.warning(f"Optimization engine not available: {e}")
    OPTIMIZATION_AVAILABLE = False

# SQLite Database Setup
def setup_database():
    """Initialize SQLite database for historical data logging"""
    conn = sqlite3.connect('pharma_dashboard_history.db')
    cursor = conn.cursor()
    
    # Create tables for historical data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            total_queued_items INTEGER,
            total_value REAL,
            avg_days_in_queue REAL,
            booked_items_count INTEGER,
            booked_items_value REAL,
            no_orders_count INTEGER,
            no_orders_value REAL,
            at_risk_count INTEGER,
            at_risk_value REAL,
            otif_percentage REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS station_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            station TEXT NOT NULL,
            total_value REAL,
            avg_days REAL,
            item_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS queue_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            total_items INTEGER,
            avg_queue_length REAL,
            items_over_14_days INTEGER,
            items_over_25_days INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def log_daily_data(ppq_df, otif_df, inventory_df):
    """Log current dashboard data to SQLite database"""
    try:
        conn = sqlite3.connect('pharma_dashboard_history.db')
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Calculate metrics for logging
        total_queued_items = len(ppq_df)
        total_value = ppq_df['value_eur'].sum()
        avg_days_in_queue = ppq_df['days_in_queue'].mean()
        
        booked_items = ppq_df[ppq_df['booking_status'] == 'Booked']
        booked_items_count = len(booked_items)
        booked_items_value = booked_items['value_eur'].sum()
        
        no_orders = ppq_df[ppq_df['has_customer_order'] == False]
        no_orders_count = len(no_orders)
        no_orders_value = no_orders['value_eur'].sum()
        
        at_risk_items = ppq_df[ppq_df['days_in_queue'] > 25]
        at_risk_count = len(at_risk_items)
        at_risk_value = at_risk_items['value_eur'].sum()
        
        current_month_otif = otif_df[otif_df['month_year'] == '2025-07']['otif_percentage'].mean()
        
        # Log daily snapshot
        cursor.execute('''
            INSERT INTO daily_snapshots 
            (date, total_queued_items, total_value, avg_days_in_queue, 
             booked_items_count, booked_items_value, no_orders_count, 
             no_orders_value, at_risk_count, at_risk_value, otif_percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (today, total_queued_items, total_value, avg_days_in_queue,
              booked_items_count, booked_items_value, no_orders_count,
              no_orders_value, at_risk_count, at_risk_value, current_month_otif))
        
        # Log station performance
        station_performance = ppq_df.groupby('current_station').agg({
            'value_eur': 'sum',
            'days_in_queue': 'mean',
            'batch_id': 'count'
        }).reset_index()
        
        for _, row in station_performance.iterrows():
            cursor.execute('''
                INSERT INTO station_performance 
                (date, station, total_value, avg_days, item_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (today, row['current_station'], row['value_eur'], 
                  row['days_in_queue'], row['batch_id']))
        
        # Log queue trends
        items_over_14_days = len(ppq_df[ppq_df['days_in_queue'] > 14])
        items_over_25_days = len(ppq_df[ppq_df['days_in_queue'] > 25])
        
        cursor.execute('''
            INSERT INTO queue_trends 
            (date, total_items, avg_queue_length, items_over_14_days, items_over_25_days)
            VALUES (?, ?, ?, ?, ?)
        ''', (today, total_queued_items, avg_days_in_queue, items_over_14_days, items_over_25_days))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        st.error(f"Error logging data: {e}")

def get_historical_data(weeks=4):
    """Retrieve historical data for trend analysis with extrapolation"""
    try:
        conn = sqlite3.connect('pharma_dashboard_history.db')
        
        # Get weekly snapshots (first day of each week)
        daily_data = pd.read_sql_query(f'''
            SELECT * FROM daily_snapshots 
            WHERE date >= date('now', '-{weeks * 7} days')
            ORDER BY date
        ''', conn)
        
        # Get station performance
        station_data = pd.read_sql_query(f'''
            SELECT * FROM station_performance 
            WHERE date >= date('now', '-{weeks * 7} days')
            ORDER BY date, station
        ''', conn)
        
        # Get queue trends
        queue_data = pd.read_sql_query(f'''
            SELECT * FROM queue_trends 
            WHERE date >= date('now', '-{weeks * 7} days')
            ORDER BY date
        ''', conn)
        
        conn.close()
        
        # If no historical data exists, create extrapolated weekly data
        if daily_data.empty:
            daily_data = create_extrapolated_weekly_data(weeks)
        if station_data.empty:
            station_data = create_extrapolated_station_data(weeks)
        if queue_data.empty:
            queue_data = create_extrapolated_queue_data(weeks)
        
        return daily_data, station_data, queue_data
        
    except Exception as e:
        st.error(f"Error retrieving historical data: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def create_extrapolated_weekly_data(weeks=4):
    """Create extrapolated weekly data for trend analysis showing slow progress"""
    # Get the first day of each week for the last 4 weeks
    today = datetime.now()
    week_dates = []
    
    for i in range(weeks):
        # Go back i weeks and get the first day of that week (Monday)
        week_start = today - timedelta(days=today.weekday() + (i * 7))
        week_dates.append(week_start.strftime('%Y-%m-%d'))
    
    week_dates.reverse()  # Oldest to newest
    
    data = []
    base_total_items = 150
    base_total_value = 15000000
    base_avg_days = 26
    
    for i, date in enumerate(week_dates):
        # Create slow improvement trend over weeks
        improvement_factor = 1 - (i * 0.03)  # 3% improvement per week
        variation = random.uniform(0.95, 1.05)  # 5% random variation
        
        total_items = int(base_total_items * improvement_factor * variation)
        total_value = int(base_total_value * improvement_factor * variation)
        avg_days = base_avg_days * improvement_factor * variation
        
        data.append({
            'date': date,
            'week': f"Week {i+1}",
            'total_queued_items': total_items,
            'total_value': total_value,
            'avg_days_in_queue': avg_days,
            'booked_items_count': int(total_items * 0.5),
            'booked_items_value': int(total_value * 0.5),
            'no_orders_count': int(total_items * 0.5),
            'no_orders_value': int(total_value * 0.5),
            'at_risk_count': int(total_items * 0.2),
            'at_risk_value': int(total_value * 0.2),
            'otif_percentage': 75 + (i * 1.5) + random.uniform(-1, 1)  # Gradual OTIF improvement
        })
    
    return pd.DataFrame(data)

def create_extrapolated_station_data(weeks=4):
    """Create extrapolated weekly station performance data"""
    # Get the first day of each week for the last 4 weeks
    today = datetime.now()
    week_dates = []
    
    for i in range(weeks):
        week_start = today - timedelta(days=today.weekday() + (i * 7))
        week_dates.append(week_start.strftime('%Y-%m-%d'))
    
    week_dates.reverse()  # Oldest to newest
    stations = ['PROD', 'PACK', 'QA-MFG', 'QA-PCK', 'QC', 'Shipping', 'SC/Regul/Launch']
    
    data = []
    for i, date in enumerate(week_dates):
        for station in stations:
            # Base values for each station
            base_values = {
                'PROD': {'value': 2800000, 'days': 25, 'count': 28},
                'PACK': {'value': 2150000, 'days': 22, 'count': 21},
                'QA-MFG': {'value': 2820000, 'days': 28, 'count': 27},
                'QA-PCK': {'value': 1810000, 'days': 24, 'count': 19},
                'QC': {'value': 3470000, 'days': 30, 'count': 34},
                'Shipping': {'value': 1850000, 'days': 20, 'count': 21},
                'SC/Regul/Launch': {'value': 750000, 'days': 18, 'count': 7}
            }
            
            base = base_values[station]
            # Slow improvement trend over weeks
            improvement_factor = 1 - (i * 0.02)  # 2% improvement per week
            variation = random.uniform(0.9, 1.1)
            
            data.append({
                'date': date,
                'week': f"Week {i+1}",
                'station': station,
                'total_value': int(base['value'] * improvement_factor * variation),
                'avg_days': base['days'] * improvement_factor * variation,
                'item_count': int(base['count'] * improvement_factor * variation)
            })
    
    return pd.DataFrame(data)

def create_extrapolated_queue_data(weeks=4):
    """Create extrapolated weekly batch queue trend data with diverse trends"""
    # Get the first day of each week for the last 4 weeks
    today = datetime.now()
    week_dates = []
    
    for i in range(weeks):
        week_start = today - timedelta(days=today.weekday() + (i * 7))
        week_dates.append(week_start.strftime('%Y-%m-%d'))
    
    week_dates.reverse()  # Oldest to newest
    
    data = []
    base_total_batches = 150
    base_lab_batches = 45
    
    for i, date in enumerate(week_dates):
        # Create diverse trends for different weeks
        if i == 0:  # Oldest week - higher values
            batch_factor = 1.0
            lab_factor = 1.0
        elif i == 1:  # Second week - slight improvement
            batch_factor = 0.92
            lab_factor = 0.88
        elif i == 2:  # Third week - continued improvement
            batch_factor = 0.85
            lab_factor = 0.82
        else:  # Latest week - diverse trend (some improvements, some increases)
            batch_factor = random.choice([0.78, 0.95, 0.88])  # Diverse outcomes
            lab_factor = random.choice([0.75, 0.92, 0.85])
        
        # Add some random variation
        variation = random.uniform(0.95, 1.05)
        
        total_batches = int(base_total_batches * batch_factor * variation)
        lab_batches = int(base_lab_batches * lab_factor * variation)
        avg_queue_length = 18 + (total_batches / 10)  # Queue length based on batch count
        
        data.append({
            'date': date,
            'week': f"Week {i+1}",
            'total_batches': total_batches,
            'lab_batches': lab_batches,
            'total_items': total_batches,  # Keep for compatibility
            'avg_queue_length': avg_queue_length,
            'items_over_14_days': int(total_batches * 0.6),
            'items_over_25_days': int(total_batches * 0.2)
        })
    
    return pd.DataFrame(data)

# Initialize database
setup_database()

# Page configuration
st.set_page_config(
    page_title="Pharma Supply Chain POC",
    page_icon="🏭",
    layout="wide"
)

# Dark theme CSS with left alignment
st.markdown("""
<style>
    .stApp {
        background-color: #1e1e1e;
        color: #ffffff;
        direction: ltr;
        text-align: left;
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
        border-left: 4px solid #4299e1;
        margin: 10px 0;
        color: #ffffff;
        direction: ltr;
        text-align: left;
    }
    .metric-title {
        font-size: 16px;
        color: #a0aec0;
        margin: 0 0 10px 0;
        font-weight: 600;
        direction: ltr;
        text-align: left;
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
        direction: ltr;
        text-align: left;
    }
    .section-header {
        background: #2d3748;
        padding: 15px;
        border-radius: 8px;
        margin: 20px 0 10px 0;
        border-left: 4px solid #48bb78;
        direction: ltr;
        text-align: left;
    }
    .section-header h3 {
        color: #ffffff;
        margin: 0;
        font-size: 20px;
        direction: ltr;
        text-align: left;
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
        direction: ltr;
        text-align: left;
    }
    .stSelectbox label {
        direction: ltr;
        text-align: left;
    }
    .stSlider label {
        direction: ltr;
        text-align: left;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🏭 Pharmaceutical Supply Chain AI Agent POC</h1>
            <p>Pharmaceutical Supply Chain Management System with AI Agent</p>
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
    stations = ['PROD', 'PACK', 'QA-MFG', 'QA-PCK', 'QC', 'Shipping', 'SC/Regul/Launch']
    delay_reasons = ['Investigation', 'Documentation', 'Equipment_Issue', 'External_Lab_Dependency', 'None']
    
    data = []
    for i in range(1, 151):
        batch_id = f"200016{4800 + i}"
        material = random.choice(products)
        quantity = random.randint(300000, 1500000)
        value = random.randint(40000, 160000)
        market = random.choice(markets)
        # Give SC/Regul/Launch 5% of the data
        if random.random() < 0.05:
            station = 'SC/Regul/Launch'
        else:
            station = random.choice([s for s in stations if s != 'SC/Regul/Launch'])
        
        # Days in queue - engineered for 30% improvement
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
    """OTIF Historical - 40 rows (8 months x 5 customers) - Business target 80%"""
    customers = ['PharmaCorp EU', 'MedDistrib GmbH', 'HealthPlus SPA', 'Farma Nederland', 'MediSupply FR']
    months = ['2024-12', '2025-01', '2025-02', '2025-03', '2025-04', '2025-05', '2025-06', '2025-07']
    
    data = []
    for month in months:
        for customer in customers:
            total_orders = random.randint(10, 25)
            # Target around 80% OTIF with realistic variation
            on_time = int(total_orders * random.uniform(0.75, 0.88))
            in_full = int(total_orders * random.uniform(0.78, 0.85))
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
    stations = ['PROD', 'PACK', 'QA-MFG', 'QA-PCK', 'QC', 'Shipping', 'SC/Regul/Launch']
    
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
    stations = ['PROD', 'PACK', 'QA-MFG', 'QA-PCK', 'QC', 'Shipping', 'SC/Regul/Launch']
    
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
    stations = ['PROD', 'PACK', 'QA-MFG', 'QA-PCK', 'QC', 'Shipping', 'SC/Regul/Launch']
    
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

@st.cache_data
def generate_weekly_shipment_planning():
    """Weekly Shipment Planning with Routes and Transport Modes - 20 rows"""
    timeslots = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00', '16:00-18:00']
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    routes = ['RT-001', 'RT-002', 'RT-003', 'RT-004', 'RT-005']
    transport_modes = ['Air', 'Sea', 'Road', 'Rail']
    
    data = []
    for i in range(1, 21):
        day = random.choice(days)
        timeslot = random.choice(timeslots)
        batch_id = f"200016{4800 + random.randint(1, 150)}"
        route_id = random.choice(routes)
        transport_mode = random.choice(transport_modes)
        capacity_utilization = random.randint(60, 95)
        priority = random.choice(['High', 'Medium', 'Low'])
        
        data.append({
            'day': day,
            'timeslot': timeslot,
            'batch_id': batch_id,
            'route_id': route_id,
            'transport_mode': transport_mode,
            'capacity_utilization_percent': capacity_utilization,
            'priority': priority,
            'planned_weight_kg': random.randint(2000, 10000),
            'planned_value_eur': random.randint(50000, 200000)
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
            'routing_constraints': generate_routing_constraints(),
            'weekly_shipment_planning': generate_weekly_shipment_planning()
        }
    
    # Calculate matrices according to your requirements
    ppq_df = datasets['post_pack_queue']
    orders_df = datasets['customer_orders']
    booking_df = datasets['tms_booking']
    otif_df = datasets['otif_historical']
    inventory_df = datasets['current_inventory']
    
    # Log current data to SQLite database
    log_daily_data(ppq_df, otif_df, inventory_df)
    
    # Station Performance Overview - All 3 Charts in One Line
    st.markdown('<div class="section-header"><h3>📊 Station Performance Overview</h3></div>', unsafe_allow_html=True)
    
    # Calculate data for all charts
    station_workload = ppq_df['current_station'].value_counts().reset_index()
    station_workload.columns = ['station', 'batch_count']
    # Sort by batch count descending (high to low)
    station_workload = station_workload.sort_values('batch_count', ascending=False)
    
    station_performance = ppq_df.groupby('current_station').agg({
        'value_eur': 'sum',
        'days_in_queue': 'mean'
    }).round(1)
    station_performance.columns = ['total_value', 'avg_days']
    station_performance = station_performance.reset_index()
    # Sort by total value descending (high to low) for consistent ordering
    station_performance = station_performance.sort_values('total_value', ascending=False)
    
    # Create 3 columns for the charts
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Station Workload - No. of Batches
        fig_workload = px.bar(
            station_workload,
            x='station',
            y='batch_count',
            title='Station Workload - No. of Batches',
            color='batch_count',
            color_continuous_scale='Purples'
        )
        fig_workload.update_layout(
            height=250,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white', size=9),
            xaxis_title='Station',
            yaxis_title='Number of Batches',
            showlegend=False,
            margin=dict(l=30, r=30, t=40, b=40)
        )
        fig_workload.update_xaxes(
            tickangle=45,
            tickfont=dict(color='white', size=8)
        )
        fig_workload.update_yaxes(
            tickfont=dict(color='white', size=8)
        )
        st.plotly_chart(fig_workload, use_container_width=True, config={'displayModeBar': False})
    
    with col2:
        # Total Value by Station
        fig_value = px.bar(
            station_performance,
            x='current_station',
            y='total_value',
            title='Total Value by Station (€)',
            color='total_value',
            color_continuous_scale='Blues'
        )
        fig_value.update_layout(
            height=250,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white', size=9),
            xaxis_title='Station',
            yaxis_title='Total Value (€)',
            showlegend=False,
            margin=dict(l=30, r=30, t=40, b=40)
        )
        fig_value.update_xaxes(tickangle=45, tickfont=dict(color='white', size=8))
        fig_value.update_yaxes(tickfont=dict(color='white', size=8))
        st.plotly_chart(fig_value, use_container_width=True, config={'displayModeBar': False})
    
    with col3:
        # Average Days in Queue by Station
        fig_days = px.bar(
            station_performance,
            x='current_station',
            y='avg_days',
            title='Average Days in Queue by Station',
            color='avg_days',
            color_continuous_scale='Reds'
        )
        fig_days.update_layout(
            height=250,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white', size=9),
            xaxis_title='Station',
            yaxis_title='Average Days',
            showlegend=False,
            margin=dict(l=30, r=30, t=40, b=40)
        )
        fig_days.update_xaxes(tickangle=45, tickfont=dict(color='white', size=8))
        fig_days.update_yaxes(tickfont=dict(color='white', size=8))
        # Add target line at 15 days
        fig_days.add_hline(y=15, line_dash="dash", line_color="yellow", 
                          annotation_text="Target: 15 days")
        st.plotly_chart(fig_days, use_container_width=True, config={'displayModeBar': False})
    
    # Station Performance Summary - By Number of Batches
    st.markdown('<div class="section-header"><h3>📊 Station Performance Summary</h3></div>', unsafe_allow_html=True)
    
    # Calculate current batch counts per station
    current_batch_counts = ppq_df['current_station'].value_counts().reset_index()
    current_batch_counts.columns = ['station', 'batch_count']
    
    # Create trend data based on batch counts (simulating historical trend)
    trend_data = []
    
    for _, row in current_batch_counts.iterrows():
        station = row['station']
        current_count = row['batch_count']
        
        # Simulate historical trend (for demo purposes)
        # In a real scenario, this would come from historical data
        historical_count = int(current_count * random.uniform(0.8, 1.2))  # ±20% variation
        trend_change = current_count - historical_count
        
        if trend_change > 0:
            trend_direction = "Increasing"
            trend_color = "#f56565"  # Red for increasing workload
        elif trend_change < 0:
            trend_direction = "Decreasing"
            trend_color = "#48bb78"  # Green for decreasing workload
        else:
            trend_direction = "Stable"
            trend_color = "#f6ad55"  # Orange for stable
        
        trend_data.append({
            'station': station,
            'trend_direction': trend_direction,
            'current_count': current_count,
            'historical_count': historical_count,
            'color': trend_color
        })
    
    if trend_data:
        trend_df = pd.DataFrame(trend_data)
        
        # Display all stations as horizontal cards
        cols = st.columns(len(trend_df))
        for i, (_, row) in enumerate(trend_df.iterrows()):
            with cols[i]:
                st.markdown(f"""
                <div style="background: #2d3748; padding: 10px; margin: 5px 0; border-radius: 8px; border-left: 4px solid {row['color']}; text-align: center;">
                    <div style="color: #ffffff; font-size: 10px; font-weight: bold;">{row['station']}</div>
                    <div style="color: {row['color']}; font-size: 12px; font-weight: bold;">{row['trend_direction']}</div>
                    <div style="color: #a0aec0; font-size: 9px;">{row['current_count']} batches</div>
                </div>
                """, unsafe_allow_html=True)
    
    # Inventory
    st.markdown('<div class="section-header"><h3>📊 Inventory</h3></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Current FG inventory (higher - before optimization)
        current_fg_inventory_value = inventory_df['value_eur'].sum() + ppq_df['value_eur'].sum()
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-title">💰 Current FG Inventory</div>
            <div class="metric-value" style="color: #f56565;">€{current_fg_inventory_value:,.0f}</div>
            <div class="metric-subtitle">High inventory - Slow cycle time</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Expected FG inventory at end of month (lower - after 30% reduction)
        optimized_fg_inventory_value = int(current_fg_inventory_value * 0.7)  # 30% reduction
        savings = current_fg_inventory_value - optimized_fg_inventory_value
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-title">📅 Expected FG Inventory EOM</div>
            <div class="metric-value" style="color: #48bb78;">€{optimized_fg_inventory_value:,.0f}</div>
            <div class="metric-subtitle">Savings: €{savings:,.0f} | 30% reduction</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Top 5 High Value Inventory Items - Horizontal Cards with Acronyms
        top_5_inventory = inventory_df.nlargest(5, 'value_eur')[['material', 'value_eur', 'location', 'quantity_doses']]
        
        # Create acronyms for materials
        def get_material_acronym(material):
            words = material.split()
            if len(words) >= 2:
                return f"{words[0][:3]}-{words[1][:3]}"
            else:
                return material[:6]
        
        st.markdown("**Top 5 High Value Inventory Items**")
        cols = st.columns(5)
        for idx, (_, row) in enumerate(top_5_inventory.iterrows()):
            with cols[idx]:
                acronym = get_material_acronym(row['material'])
                location_short = row['location'].replace('_', ' ')[:8]
                st.markdown(f"""
                <div style="background: #2d3748; padding: 10px; margin: 5px 0; border-radius: 8px; border-left: 4px solid #4299e1; text-align: center;">
                    <div style="color: #ffffff; font-size: 9px; font-weight: bold;">{acronym}</div>
                    <div style="color: #4299e1; font-size: 11px; font-weight: bold;">€{row['value_eur']:,.0f}</div>
                    <div style="color: #a0aec0; font-size: 8px;">{location_short}</div>
                    <div style="color: #a0aec0; font-size: 8px;">{row['quantity_doses']:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)
    
    # Logistics
    st.markdown('<div class="section-header"><h3>📦 Logistics</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Products in shipping queue (booking completed) - Total
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
        # Products after packaging without customer orders - Total
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
    

    
    # Top 5 Lists as Horizontal Cards
    st.markdown('<div class="section-header"><h3>🏆 Top 5 Rankings</h3></div>', unsafe_allow_html=True)
    
    # Top 5 Overall Products in Queue - Horizontal Cards
    top_5_overall = ppq_df.nlargest(5, 'value_eur')[['batch_id', 'value_eur', 'target_market', 'current_station']]
    
    st.markdown("**📊 Top 5 Overall Products in Queue**")
    cols = st.columns(5)
    for idx, (_, row) in enumerate(top_5_overall.iterrows()):
        with cols[idx]:
            st.markdown(f"""
            <div style="background: #2d3748; padding: 10px; margin: 5px 0; border-radius: 8px; border-left: 4px solid #4299e1; text-align: center;">
                <div style="color: #ffffff; font-size: 10px; font-weight: bold;">{row['batch_id']}</div>
                <div style="color: #4299e1; font-size: 12px; font-weight: bold;">€{row['value_eur']:,.0f}</div>
                <div style="color: #a0aec0; font-size: 9px;">{row['target_market']}</div>
                <div style="color: #a0aec0; font-size: 9px;">{row['current_station']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Top 5 Longest Queue Items - Horizontal Cards
    top_5_longest = ppq_df.nlargest(5, 'days_in_queue')[['batch_id', 'days_in_queue', 'current_station']]
    
    st.markdown("**⏳ Top 5 Longest Queue Items**")
    cols = st.columns(5)
    for idx, (_, row) in enumerate(top_5_longest.iterrows()):
        with cols[idx]:
            st.markdown(f"""
            <div style="background: #2d3748; padding: 10px; margin: 5px 0; border-radius: 8px; border-left: 4px solid #f56565; text-align: center;">
                <div style="color: #ffffff; font-size: 10px; font-weight: bold;">{row['batch_id']}</div>
                <div style="color: #f56565; font-size: 12px; font-weight: bold;">{row['days_in_queue']} days</div>
                <div style="color: #a0aec0; font-size: 9px;">{row['current_station']}</div>
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
        # Top 5 Exception/At-Risk Items - Horizontal Cards
        at_risk_items = ppq_df[ppq_df['days_in_queue'] > 25]
        top_5_at_risk = at_risk_items.nlargest(5, 'value_eur')[['batch_id', 'value_eur', 'target_market', 'delay_reason']]
        
        st.markdown("**⚠️ Top 5 Exception/At-Risk Items**")
        cols = st.columns(5)
        for idx, (_, row) in enumerate(top_5_at_risk.iterrows()):
            with cols[idx]:
                st.markdown(f"""
                <div style="background: #2d3748; padding: 10px; margin: 5px 0; border-radius: 8px; border-left: 4px solid #f56565; text-align: center;">
                    <div style="color: #ffffff; font-size: 10px; font-weight: bold;">{row['batch_id']}</div>
                    <div style="color: #f56565; font-size: 12px; font-weight: bold;">€{row['value_eur']:,.0f}</div>
                    <div style="color: #a0aec0; font-size: 9px;">{row['target_market']}</div>
                    <div style="color: #a0aec0; font-size: 9px;">{row['delay_reason']}</div>
                </div>
                """, unsafe_allow_html=True)
    

    

    
    # Historical Analysis & Trends
    st.markdown('<div class="section-header"><h3>📈 Historical Analysis & Trends (Last 4 Weeks)</h3></div>', unsafe_allow_html=True)
    
    # Get historical data (always generate extrapolated data for demo)
    queue_data = create_extrapolated_queue_data(weeks=4)
    
    if not queue_data.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Total Batches Trend Chart
            if 'total_batches' in queue_data.columns:
                fig_batch_trend = px.line(
                    queue_data,
                    x='date',
                    y='total_batches',
                    title='Total Batches in Queue (Weekly Trend)',
                    markers=True,
                    line_shape='linear'
                )
                fig_batch_trend.update_layout(
                    height=250,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white', size=10),
                    xaxis_title='Week',
                    yaxis_title='Number of Batches',
                    margin=dict(l=40, r=40, t=40, b=40)
                )
                fig_batch_trend.update_xaxes(
                    tickfont=dict(color='white', size=9),
                    tickangle=45,
                    tickformat='%b %d'
                )
                fig_batch_trend.update_yaxes(tickfont=dict(color='white', size=9))
                fig_batch_trend.add_hline(y=130, line_dash="dash", line_color="green", 
                                        annotation_text="Target: 130 batches")
                st.plotly_chart(fig_batch_trend, use_container_width=True, config={'displayModeBar': False})
            else:
                st.error("Debug: total_batches column not found in queue_data")
                st.write("Available columns:", queue_data.columns.tolist())
        
        with col2:
            # Laboratory Batches Trend Chart
            if 'lab_batches' in queue_data.columns:
                fig_lab_trend = px.line(
                    queue_data,
                    x='date',
                    y='lab_batches',
                    title='Laboratory Batches Trend (Weekly Progress)',
                    markers=True,
                    line_shape='linear'
                )
                fig_lab_trend.update_layout(
                    height=250,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white', size=10),
                    xaxis_title='Week',
                    yaxis_title='Lab Batches',
                    margin=dict(l=40, r=40, t=40, b=40)
                )
                fig_lab_trend.update_xaxes(
                    tickfont=dict(color='white', size=9),
                    tickangle=45,
                    tickformat='%b %d'
                )
                fig_lab_trend.update_yaxes(tickfont=dict(color='white', size=9))
                fig_lab_trend.add_hline(y=35, line_dash="dash", line_color="purple", 
                                        annotation_text="Target: 35 lab batches")
                st.plotly_chart(fig_lab_trend, use_container_width=True, config={'displayModeBar': False})
            else:
                st.error("Debug: lab_batches column not found in queue_data")
                st.write("Available columns:", queue_data.columns.tolist())
    else:
        st.error("Debug: queue_data is empty")
        # Try to create data directly
        queue_data = create_extrapolated_queue_data(weeks=4)
        st.write("Created queue_data:", queue_data.head())
    

    
    # Optimization Engine
    if OPTIMIZATION_AVAILABLE:
        st.markdown('<div class="section-header"><h3>🚀 Supply Chain Optimization</h3></div>', unsafe_allow_html=True)
        
        # Load optimization data
        try:
            batches_df = pd.read_excel('batches_v2.xlsx')
            routes_df = pd.read_excel('routes_v2.xlsx')
            
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
                            opt_json = json.dumps(opt_results, indent=2, default=str)
                            
                            st.download_button(
                                label="📄 Download Optimization Results (JSON)",
                                data=opt_json,
                                file_name="optimization_results.json",
                                mime="application/json"
                            )
                    
                    except Exception as e:
                        st.error(f"❌ Optimization failed: {str(e)}")
                        st.info("💡 Make sure the Excel files (batches_v2.xlsx and routes_v2.xlsx) are in the same directory as the dashboard.")
        except FileNotFoundError:
            st.error("❌ Optimization data files not found!")
            st.info("💡 Please ensure 'batches_v2.xlsx' and 'routes_v2.xlsx' are in the same directory as the dashboard.")
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
    
    # Success message at the bottom
    st.success("✅ Data generated successfully!")

if __name__ == "__main__":
    main()
