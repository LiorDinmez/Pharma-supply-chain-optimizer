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

# Fixed optimization import
try:
    from optimization_engine_v2 import AdvancedOptimizationEngine
    OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    OPTIMIZATION_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Pharma Supply Chain POC",
    page_icon="🏭",
    layout="wide"
)

# Your existing CSS
st.markdown("""
<style>
    .stApp {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    .main-header {
        background: linear-gradient(90deg, #2d3748 0%, #4a5568 100%);
        padding: 20px;
        border-radius: 10px;
        color: #ffffff;
        text-align: center;
        margin-bottom: 30px;
    }
    .metric-container {
        background: #2d3748;
        padding: 20px;
        border-radius: 10px;
        border-right: 4px solid #4299e1;
        margin: 10px 0;
        color: #ffffff;
    }
    .metric-title {
        font-size: 16px;
        color: #a0aec0;
        margin: 0 0 10px 0;
        font-weight: 600;
    }
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        margin: 10px 0;
        text-align: center;
    }
    .metric-subtitle {
        font-size: 14px;
        color: #a0aec0;
        margin: 5px 0 0 0;
    }
    .section-header {
        background: #2d3748;
        padding: 15px;
        border-radius: 8px;
        margin: 20px 0 10px 0;
        border-right: 4px solid #48bb78;
    }
    .section-header h3 {
        color: #ffffff;
        margin: 0;
        font-size: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🏭 Pharmaceutical Supply Chain POC</h1>
    <p>AI-Powered Supply Chain Management System</p>
</div>
""", unsafe_allow_html=True)

@st.cache_data
def generate_post_pack_queue():
    """Post Pack Queue - 150 rows"""
    products = [
        'ZONISAMIDE 25MG', 'LAMOTRIGINE TABLETS', 'CARBAMAZEPINE 200MG',
        'GABAPENTIN 300MG', 'PREGABALIN 75MG', 'TOPIRAMATE 100MG',
        'LEVETIRACETAM 500MG', 'VALPROATE 250MG', 'PHENYTOIN 100MG'
    ]
    
    markets = ['DE', 'HU', 'FR', 'IT', 'ES', 'NL', 'BE', 'AT', 'PL']
    stations = ['PROD', 'PACK', 'QA-MFG', 'QA-PCK', 'QC', 'SC', 'Regulation/Launch', 'Shipping']
    delay_reasons = ['Investigation', 'Documentation', 'Equipment_Issue', 'External_Lab_Dependency', 'None']
    
    data = []
    for i in range(1, 151):
        batch_id = f"200016{4800 + i}"
        material = random.choice(products)
        quantity = random.randint(300000, 1500000)
        value = random.randint(40000, 160000)
        market = random.choice(markets)
        weight_kg = random.uniform(200, 1000)
        volume_m3 = random.uniform(1.5, 6.0)
        
        # Station distribution
        station_choice = random.random()
        if station_choice < 0.05:
            station = 'SC'
        elif station_choice < 0.10:
            station = 'Regulation/Launch'
            value = random.randint(80000, 250000)
        else:
            station = random.choice(['PROD', 'PACK', 'QA-MFG', 'QA-PCK', 'QC', 'Shipping'])
        
        # Days in queue
        if random.random() < 0.7:
            days_in_queue = random.randint(8, 25)
            delay_reason = 'None'
        else:
            days_in_queue = random.randint(40, 70)
            delay_reason = random.choice([r for r in delay_reasons if r != 'None'])
        
        packaging_date = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d')
        expected_release = (datetime.now() + timedelta(days=random.randint(1, 45))).strftime('%Y-%m-%d')
        
        # Customer orders
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
            'value_eur': value,
            'weight_kg': weight_kg,
            'volume_m3': volume_m3,
            'packaging_completion_date': packaging_date,
            'current_station': station,
            'target_market': market,
            'expected_release_date': expected_release,
            'delay_reason': delay_reason,
            'days_in_queue': days_in_queue,
            'has_customer_order': has_customer_order,
            'days_after_packaging': days_after_packaging,
            'booking_status': booking_status
        })
    
    return pd.DataFrame(data)

@st.cache_data
def generate_routes_for_optimization():
    """Generate routes data compatible with optimization engine"""
    data = []
    for i in range(1, 16):
        route_id = f"RT-{i:03d}"
        origin = random.choice(['Production_EU', 'Packaging_US', 'Testing_APAC'])
        destination = random.choice(['North_America', 'Europe', 'Asia_Pacific', 'Latin_America'])
        mode = random.choice(['Air_Express', 'Air_Standard', 'Ground_Express', 'Ground_Standard', 'Ocean_Standard'])
        capacity_kg = random.randint(5000, 35000)
        capacity_m3 = random.randint(25, 200)
        cost_per_kg = round(random.uniform(1.5, 15.0), 2)
        transit_days = random.randint(1, 25)
        
        data.append({
            'route_id': route_id,
            'origin': origin,
            'destination_region': destination,
            'transport_mode': mode,
            'capacity_kg': capacity_kg,
            'capacity_m3': capacity_m3,
            'cost_per_kg': cost_per_kg,
            'transit_days': transit_days
        })
    
    return pd.DataFrame(data)

def main():
    # Week info
    today = datetime.now().date()
    week_number = today.isocalendar()[1]
    year = today.year
    import calendar
    last_day_of_month = calendar.monthrange(year, today.month)[1]
    days_remaining = last_day_of_month - today.day
    
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
    
    # Generate data
    with st.spinner("🔄 Generating data..."):
        ppq_df = generate_post_pack_queue()
        routes_df = generate_routes_for_optimization()
    
    st.success("✅ Data generated successfully!")
    
    # Station Workload
    st.markdown('<div class="section-header"><h3>📊 Station Workload - No. of Batches</h3></div>', unsafe_allow_html=True)
    
    station_workload = ppq_df['current_station'].value_counts().reset_index()
    station_workload.columns = ['station', 'batch_count']
    
    fig_workload = px.bar(
        station_workload,
        x='station',
        y='batch_count',
        title='Number of Batches Pending by Station',
        color='batch_count',
        color_continuous_scale='Purples'
    )
    
    fig_workload.update_layout(
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=12),
        xaxis_title='Station',
        yaxis_title='Number of Batches',
        showlegend=False
    )
    
    st.plotly_chart(fig_workload, use_container_width=True, config={'displayModeBar': False})
    
    # Performance by Station
    st.markdown('<div class="section-header"><h3>📊 Performance by Station</h3></div>', unsafe_allow_html=True)
    
    station_performance = ppq_df.groupby('current_station').agg({
        'value_eur': 'sum',
        'days_in_queue': 'mean'
    }).round(1)
    station_performance.columns = ['total_value', 'avg_days']
    station_performance = station_performance.reset_index()
    
    col1, col2 = st.columns(2)
    
    with col1:
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
            showlegend=False
        )
        fig_value.update_xaxes(tickangle=45)
        st.plotly_chart(fig_value, use_container_width=True)
    
    with col2:
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
            showlegend=False
        )
        fig_days.update_xaxes(tickangle=45)
        fig_days.add_hline(y=15, line_dash="dash", line_color="yellow", 
                          annotation_text="Target: 15 days")
        st.plotly_chart(fig_days, use_container_width=True)
    
    # Logistics KPIs
    st.markdown('<div class="section-header"><h3>📦 Logistics</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
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
        current_month_otif = 78.5  # Sample OTIF
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-title">🎯 Expected OTIF End of Month</div>
            <div class="metric-value" style="color: {'#48bb78' if current_month_otif >= 80 else '#f56565'};">{current_month_otif:.1f}%</div>
            <div class="metric-subtitle">Target: 80%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
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
        current_inventory_value = ppq_df['value_eur'].sum() * 1.2
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-title">💰 Current Inventory</div>
            <div class="metric-value" style="color: #f56565;">€{current_inventory_value:,.0f}</div>
            <div class="metric-subtitle">High inventory - Slow cycle time</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        optimized_inventory_value = int(current_inventory_value * 0.7)
        savings = current_inventory_value - optimized_inventory_value
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-title">📅 Expected Inventory End of Month</div>
            <div class="metric-value" style="color: #48bb78;">€{optimized_inventory_value:,.0f}</div>
            <div class="metric-subtitle">Savings: €{savings:,.0f} | 30% reduction</div>
        </div>
        """, unsafe_allow_html=True)
    
    # FIXED OPTIMIZATION ENGINE
    if OPTIMIZATION_AVAILABLE:
        st.markdown('<div class="section-header"><h3>🚀 Supply Chain Optimization</h3></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📊 Batch Data Preview:**")
            st.dataframe(ppq_df.head(), use_container_width=True)
        
        with col2:
            st.markdown("**🛣️ Routes Data Preview:**")
            st.dataframe(routes_df.head(), use_container_width=True)
        
        # Optimization parameters
        st.markdown("**⚙️ Optimization Parameters:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            alpha = st.slider("Risk Weight (α)", 0.0, 0.1, 0.01, 0.001)
        
        with col2:
            max_transit = st.slider("Max Transit Days", 7, 30, 21)
        
        with col3:
            monte_carlo_iter = st.slider("Monte Carlo Iterations", 500, 5000, 2000, 500)
        
        # Run optimization
        if st.button("🚀 Run Optimization", type="primary"):
            with st.spinner("Running optimization engine..."):
                try:
                    engine = AdvancedOptimizationEngine()
                    
                    constraints = {
                        "alpha": alpha,
                        "max_transit_days": max_transit,
                        "min_otif_rate": 0.8
                    }
                    
                    result = engine.optimize_shipment_plan(ppq_df, routes_df, constraints)
                    
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
                        st.metric(
                            "Risk Score",
                            f"{risk_score:.1f}",
                            delta="Low Risk" if risk_score < 30 else "High Risk"
                        )
                    
                    # Optimization plan
                    st.markdown("**📋 Optimization Plan:**")
                    optimized_plan = result.get('optimized_plan', [])
                    if optimized_plan:
                        plan_df = pd.DataFrame(optimized_plan)
                        st.dataframe(plan_df, use_container_width=True)
                    
                    # Approval
                    st.markdown("**🤔 Do you approve this optimization plan?**")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("✅ Yes, Apply Optimization", type="primary"):
                            st.success("🎉 Optimization plan approved and applied!")
                    
                    with col2:
                        if st.button("❌ No, Keep Current Plan"):
                            st.warning("⚠️ Optimization plan rejected.")
                
                except Exception as e:
                    st.error(f"❌ Optimization failed: {str(e)}")
    else:
        st.warning("⚠️ Optimization engine not available.")
    
    # Data Display
    st.markdown('<div class="section-header"><h3>👀 Raw Data</h3></div>', unsafe_allow_html=True)
    st.dataframe(ppq_df, use_container_width=True)

if __name__ == "__main__":
    main()
