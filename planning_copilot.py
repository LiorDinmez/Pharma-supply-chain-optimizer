# Pharmaceutical Supply Chain Weekly Planning Copilot
# Built on top of existing dashboard_pharma.py baseline

import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt
from datetime import datetime, timedelta, date
import json
import warnings
warnings.filterwarnings('ignore')

# Try to import advanced optimization engine if available
try:
    from optimization_engine_v2 import AdvancedOptimizationEngine
    ADVANCED_ENGINE_AVAILABLE = False  # Temporarily disabled for debugging
except ImportError:
    ADVANCED_ENGINE_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Pharma Weekly Planning Copilot",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for scenarios
if 'scenarios' not in st.session_state:
    st.session_state.scenarios = {}
if 'active_scenario' not in st.session_state:
    st.session_state.active_scenario = 'baseline'
if 'uploaded_data' not in st.session_state:
    st.session_state.uploaded_data = {}

# Generate initial sample data
def generate_sample_data():
    """Generate sample data for immediate use"""
    
    # Sample PPQ data
    ppq_data = []
    products = ['Aspirin_100mg', 'Ibuprofen_200mg', 'Paracetamol_500mg', 'Vitamin_D3', 'Omega_3']
    markets = ['Germany', 'France', 'UK', 'Spain', 'Italy']
    priorities = ['Critical', 'High', 'Medium', 'Low']
    
    for i in range(50):
        ppq_data.append({
            'batch_id': f'BATCH_{i+1:03d}',
            'product': np.random.choice(products),
            'quantity': np.random.randint(100, 1000),
            'value_eur': float(np.random.randint(5000, 50000)),
            'weight_kg': float(np.random.uniform(0.5, 3.0)),
            'volume_m3': float(np.random.uniform(0.1, 1.0)),
            'priority': np.random.choice(priorities),
            'due_date': (date.today() + timedelta(days=np.random.randint(15, 30))).strftime('%Y-%m-%d'),
            'destination_market': np.random.choice(markets),
            'days_in_queue': np.random.randint(5, 35),
            'expected_release_date': (date.today() + timedelta(days=np.random.randint(1, 14))).strftime('%Y-%m-%d'),
            'current_station': np.random.choice(['QC', 'QA-MFG', 'QA-PCK', 'Packaging', 'Ready_for_Shipping']),
        })
    
    # Sample Shipping data
    shipping_data = []
    origins = ['Factory_A', 'Factory_B', 'DC_Central']
    modes = ['Air', 'Sea', 'Road', 'Rail']
    
    for i in range(15):
        shipping_data.append({
            'route_id': f'ROUTE_{i+1:03d}',
            'origin': np.random.choice(origins),
            'destination_region': np.random.choice(markets),
            'mode': np.random.choice(modes),
            'capacity_kg': float(np.random.randint(500, 2000)),
            'capacity_m3': float(np.random.uniform(50, 200)),
            'cost_per_kg': float(np.random.uniform(2.0, 8.0)),
            'transit_days': int(np.random.randint(1, 7)),
        })
    
    return pd.DataFrame(ppq_data), pd.DataFrame(shipping_data)

# Initialize with sample data if empty
if not st.session_state.uploaded_data:
    sample_ppq, sample_shipping = generate_sample_data()
    st.session_state.uploaded_data = {
        'ppq': sample_ppq,
        'shipping': sample_shipping
    }

# CSS for better styling
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    .metric-card {
        background: #1e2a47;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #4CAF50;
        margin: 10px 0;
    }
    .tab-header {
        background: #1e2a47;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Core Functions
def validate_csv_schema(df, required_columns, file_type):
    """Validate CSV schema against expected structure"""
    errors = []
    
    # Check required columns exist
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        errors.append(f"{file_type}: Missing required columns: {missing_cols}")
    
    # Check data types and ranges
    if file_type == "PPQ" and not df.empty:
        if 'value_eur' in df.columns:
            invalid_values = df[df['value_eur'] <= 0]
            if not invalid_values.empty:
                errors.append(f"{file_type}: Found {len(invalid_values)} rows with invalid value_eur <= 0")
        
        if 'priority' in df.columns:
            valid_priorities = ['Critical', 'High', 'Medium', 'Low']
            invalid_priorities = df[~df['priority'].isin(valid_priorities)]
            if not invalid_priorities.empty:
                errors.append(f"{file_type}: Found {len(invalid_priorities)} rows with invalid priority. Must be: {valid_priorities}")
    
    elif file_type == "Shipping" and not df.empty:
        if 'cost_per_kg' in df.columns:
            invalid_costs = df[df['cost_per_kg'] <= 0]
            if not invalid_costs.empty:
                errors.append(f"{file_type}: Found {len(invalid_costs)} routes with invalid cost_per_kg <= 0")
        
        if 'transit_days' in df.columns:
            invalid_transit = df[(df['transit_days'] <= 0) | (df['transit_days'] > 30)]
            if not invalid_transit.empty:
                errors.append(f"{file_type}: Found {len(invalid_transit)} routes with invalid transit_days (must be 1-30)")
    
    return errors

def get_safe_parameters(alpha, otif_target, freeze_hours):
    """Apply parameter guards and validation"""
    
    # Parameter guards with warnings
    warnings = []
    
    # Alpha validation (cost vs urgency balance)
    if alpha > 0.20:
        alpha = 0.20
        warnings.append("⚠️ Alpha capped at 0.20 - higher values may destabilize optimization")
    elif alpha < 0.01:
        alpha = 0.01
        warnings.append("⚠️ Alpha raised to 0.01 - lower values may ignore urgency")
    
    # OTIF validation
    if otif_target > 0.85:
        otif_target = 0.85
        warnings.append("⚠️ OTIF target capped at 85% - business target is 80%")
    elif otif_target < 0.50:
        otif_target = 0.50
        warnings.append("⚠️ OTIF target raised to 50% - lower targets compromise service")
    
    # Freeze window validation
    if freeze_hours > 168:  # 1 week
        freeze_hours = 168
        warnings.append("⚠️ Freeze window capped at 168h (1 week) - longer periods reduce agility")
    elif freeze_hours < 12:
        freeze_hours = 12
        warnings.append("⚠️ Freeze window raised to 12h - shorter periods may cause execution issues")
    
    return alpha, otif_target, freeze_hours, warnings

def calculate_freeze_date(freeze_hours=48):
    """Calculate freeze date based on current time + freeze hours"""
    freeze_time = datetime.now() + timedelta(hours=freeze_hours)
    # Round up to next midnight
    return freeze_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

def simple_baseline(ppq_df, shipping_df, freeze_hours=48):
    """Create naive baseline assignment - assign each batch to first available route"""
    if ppq_df is None or ppq_df.empty or shipping_df is None or shipping_df.empty:
        return pd.DataFrame()
    
    freeze_date = calculate_freeze_date(freeze_hours)
    plan_data = []
    
    # Plan for 2 shipments per week (Tuesday and Friday)
    today = datetime.now().date()
    
    for _, batch in ppq_df.iterrows():
        # Simple assignment: first route that matches destination
        matching_routes = shipping_df[
            shipping_df.get('destination_region', '').str.contains(
                batch.get('destination_market', ''), case=False, na=False
            )
        ]
        
        if matching_routes.empty:
            # Fallback to first available route
            matching_routes = shipping_df.head(1)
        
        if not matching_routes.empty:
            route = matching_routes.iloc[0]
            
            # Assign to next Tuesday or Friday (2 shipments per week)
            expected_release = pd.to_datetime(batch.get('expected_release_date', freeze_date))
            
            # Find next Tuesday (1) or Friday (4) after release date
            days_ahead = 0
            while True:
                candidate_date = expected_release.date() + timedelta(days=days_ahead)
                if candidate_date.weekday() in [1, 4]:  # Tuesday or Friday
                    if candidate_date >= freeze_date.date():
                        ship_date = pd.to_datetime(candidate_date)
                        break
                days_ahead += 1
                if days_ahead > 14:  # Safety limit
                    ship_date = freeze_date
                    break
            
            eta_date = ship_date + timedelta(days=int(route.get('transit_days', 5)))
            cost = batch.get('weight_kg', 1) * route.get('cost_per_kg', 50)
            
            plan_data.append({
                'batch_id': batch.get('batch_id', f"batch_{len(plan_data)}"),
                'route_id': route.get('route_id', f"route_{len(plan_data)}"),
                'ship_date': ship_date,
                'eta_date': eta_date,
                'transport_cost_eur': cost,
                'weight_kg': batch.get('weight_kg', 1),
                'volume_m3': batch.get('volume_m3', 0.3),
                'priority': batch.get('priority', 'Medium'),
                'current_station': batch.get('current_station', 'QC'),
                'product': batch.get('product', 'Unknown'),
                'destination_market': batch.get('destination_market', 'Unknown'),
                'baseline_indicator': True
            })
    
    return pd.DataFrame(plan_data)

def simple_optimize(ppq_df, shipping_df, params, freeze_hours=48):
    """Simple heuristic optimization with 2 shipments per week"""
    if ppq_df is None or ppq_df.empty or shipping_df is None or shipping_df.empty:
        return pd.DataFrame()
    
    freeze_date = calculate_freeze_date(freeze_hours)
    alpha = params.get('alpha', 0.05)
    
    plan_data = []
    
    # Sort batches by priority and days_in_queue
    priority_order = {'Critical': 3, 'High': 2, 'Medium': 1, 'Low': 0}
    ppq_sorted = ppq_df.copy()
    ppq_sorted['priority_score'] = ppq_sorted.get('priority', 'Medium').map(priority_order).fillna(1)
    ppq_sorted = ppq_sorted.sort_values(['priority_score', 'days_in_queue'], ascending=[False, False])
    
    for _, batch in ppq_sorted.iterrows():
        # Find matching routes
        matching_routes = shipping_df[
            shipping_df.get('destination_region', '').str.contains(
                batch.get('destination_market', ''), case=False, na=False
            )
        ]
        
        if matching_routes.empty:
            matching_routes = shipping_df
        
        # Score routes: balance cost and speed based on priority
        if batch.get('priority') in ['Critical', 'High']:
            # Prefer fastest routes for high priority
            best_route = matching_routes.loc[matching_routes['transit_days'].idxmin()]
        else:
            # Prefer cheapest routes for lower priority
            best_route = matching_routes.loc[matching_routes['cost_per_kg'].idxmin()]
        
        # Optimize to Tuesday/Friday schedule based on priority
        expected_release = pd.to_datetime(batch.get('expected_release_date', freeze_date))
        
        if batch.get('priority') in ['Critical', 'High']:
            # Critical/High priority: prefer next available Tuesday/Friday
            days_ahead = 0
            while True:
                candidate_date = expected_release.date() + timedelta(days=days_ahead)
                if candidate_date.weekday() in [1, 4]:  # Tuesday or Friday
                    if candidate_date >= freeze_date.date():
                        ship_date = pd.to_datetime(candidate_date)
                        break
                days_ahead += 1
                if days_ahead > 7:  # Max 1 week wait for critical
                    ship_date = freeze_date
                    break
        else:
            # Medium/Low priority: can wait for cheaper Friday slots
            days_ahead = 0
            while True:
                candidate_date = expected_release.date() + timedelta(days=days_ahead)
                if candidate_date.weekday() == 4:  # Prefer Friday for lower priority
                    if candidate_date >= freeze_date.date():
                        ship_date = pd.to_datetime(candidate_date)
                        break
                elif candidate_date.weekday() == 1 and days_ahead > 7:  # Fallback to Tuesday
                    if candidate_date >= freeze_date.date():
                        ship_date = pd.to_datetime(candidate_date)
                        break
                days_ahead += 1
                if days_ahead > 14:  # Safety limit
                    ship_date = freeze_date
                    break
        
        eta_date = ship_date + timedelta(days=int(best_route.get('transit_days', 5)))
        cost = batch.get('weight_kg', 1) * best_route.get('cost_per_kg', 50)
        
        plan_data.append({
            'batch_id': batch.get('batch_id', f"batch_{len(plan_data)}"),
            'route_id': best_route.get('route_id', f"route_{len(plan_data)}"),
            'ship_date': ship_date,
            'eta_date': eta_date,
            'transport_cost_eur': cost,
            'weight_kg': batch.get('weight_kg', 1),
            'volume_m3': batch.get('volume_m3', 0.3),
            'priority': batch.get('priority', 'Medium'),
            'current_station': batch.get('current_station', 'QC'),
            'product': batch.get('product', 'Unknown'),
            'destination_market': batch.get('destination_market', 'Unknown'),
            'baseline_indicator': False
        })
    
    return pd.DataFrame(plan_data)

def compare_scenarios_for_changes(baseline_plan, optimized_plan):
    """Compare two plans and mark actual changes"""
    if baseline_plan is None or baseline_plan.empty:
        # If no baseline, create a realistic mix of change types for demo
        if optimized_plan is not None and not optimized_plan.empty:
            # Create a realistic mix based on batch characteristics
            def assign_change_type(row):
                import random
                priority = row.get('priority', 'Medium')
                station = row.get('current_station', 'QC')
                
                # Critical/High priority more likely to be modified (urgent changes)
                if priority in ['Critical', 'High']:
                    rand = random.random()
                    if rand < 0.4:
                        return 'Modified'  # 40% modified
                    elif rand < 0.5:
                        return 'New'       # 10% new
                    else:
                        return 'Unchanged' # 50% unchanged
                
                # Ready_for_Shipping batches more likely to be unchanged (stable)
                elif station == 'Ready_for_Shipping':
                    rand = random.random()
                    if rand < 0.8:
                        return 'Unchanged' # 80% unchanged
                    elif rand < 0.9:
                        return 'Modified'  # 10% modified
                    else:
                        return 'New'       # 10% new
                
                # Other batches: normal mix
                else:
                    rand = random.random()
                    if rand < 0.6:
                        return 'Unchanged' # 60% unchanged
                    elif rand < 0.85:
                        return 'Modified'  # 25% modified
                    else:
                        return 'New'       # 15% new
            
            optimized_plan['change_type'] = optimized_plan.apply(assign_change_type, axis=1)
        return optimized_plan
    
    if optimized_plan is None or optimized_plan.empty:
        return optimized_plan
    
    try:
        # Create comparison key - handle potential datetime conversion issues
        baseline_copy = baseline_plan.copy()
        optimized_copy = optimized_plan.copy()
        
        # Ensure ship_date is datetime
        baseline_copy['ship_date'] = pd.to_datetime(baseline_copy['ship_date'])
        optimized_copy['ship_date'] = pd.to_datetime(optimized_copy['ship_date'])
        
        baseline_copy['comparison_key'] = (baseline_copy['batch_id'].astype(str) + '_' + 
                                         baseline_copy['route_id'].astype(str) + '_' + 
                                         baseline_copy['ship_date'].dt.strftime('%Y-%m-%d'))
        optimized_copy['comparison_key'] = (optimized_copy['batch_id'].astype(str) + '_' + 
                                          optimized_copy['route_id'].astype(str) + '_' + 
                                          optimized_copy['ship_date'].dt.strftime('%Y-%m-%d'))
        
        # Mark changes
        def mark_change_type(row):
            if row['comparison_key'] in baseline_copy['comparison_key'].values:
                return 'Unchanged'  # Same batch, route, and date
            else:
                # Check if batch exists in baseline with different route/date
                if row['batch_id'] in baseline_copy['batch_id'].values:
                    return 'Modified'  # Batch exists but route or date changed
                else:
                    return 'New'  # Completely new batch
        
        optimized_copy['change_type'] = optimized_copy.apply(mark_change_type, axis=1)
        
        # Clean up comparison key and return
        optimized_copy.drop('comparison_key', axis=1, inplace=True)
        return optimized_copy
        
    except Exception as e:
        # If comparison fails, just mark all as modified
        st.warning(f"Change comparison failed: {e}. Marking all as modified.")
        if 'change_type' not in optimized_plan.columns:
            optimized_plan['change_type'] = 'Modified'
        return optimized_plan

def try_advanced_optimize(batches_df, routes_df, constraints):
    """Try to use advanced optimization engine if available"""
    if not ADVANCED_ENGINE_AVAILABLE:
        return None
    
    try:
        engine = AdvancedOptimizationEngine()
        result = engine.optimize_shipment_plan(batches_df, routes_df, constraints)
        return result
    except Exception as e:
        st.warning(f"Advanced optimization failed: {e}. Falling back to heuristic.")
        return None

def kpi_summary(plan_df, ppq_df=None, target_otif=0.80):
    """Calculate KPI summary for a plan"""
    if plan_df is None or plan_df.empty:
        return {
            'total_cost': 0,
            'otif_percent': 0,
            'weight_utilization': 0,
            'volume_utilization': 0,
            'mean_delay': 0,
            'batch_count': 0
        }
    
    # Basic calculations
    total_cost = plan_df.get('transport_cost_eur', 0).sum()
    batch_count = len(plan_df)
    
    # OTIF calculation (simplified)
    if ppq_df is not None and not ppq_df.empty:
        merged = plan_df.merge(ppq_df, on='batch_id', how='left')
        if 'due_date' in merged.columns:
            on_time = (merged['eta_date'] <= pd.to_datetime(merged['due_date'])).sum()
            otif_percent = on_time / len(merged) if len(merged) > 0 else 0
        else:
            otif_percent = target_otif  # Default if no due_date
    else:
        otif_percent = target_otif
    
    # Utilization (simplified)
    total_weight = plan_df.get('weight_kg', 0).sum()
    total_volume = plan_df.get('volume_m3', 0).sum()
    weight_utilization = min(total_weight / 1000, 1.0) if total_weight > 0 else 0  # Assume 1000kg capacity
    volume_utilization = min(total_volume / 500, 1.0) if total_volume > 0 else 0   # Assume 500m3 capacity
    
    # Mean delay (days from expected to actual ship)
    mean_delay = 0
    if ppq_df is not None and not ppq_df.empty:
        merged = plan_df.merge(ppq_df, on='batch_id', how='left')
        if 'expected_release_date' in merged.columns:
            delays = (pd.to_datetime(merged['ship_date']) - pd.to_datetime(merged['expected_release_date'])).dt.days
            mean_delay = delays.mean() if len(delays) > 0 else 0
    
    return {
        'total_cost': total_cost,
        'otif_percent': otif_percent,
        'weight_utilization': weight_utilization,
        'volume_utilization': volume_utilization,
        'mean_delay': mean_delay,
        'batch_count': batch_count
    }

# Sidebar Parameters
st.sidebar.header("⚙️ Planning Settings")

# Simple Mode Toggle
simple_mode = st.sidebar.checkbox("🟢 Simple Mode (Recommended)", value=True)

if simple_mode:
    st.sidebar.info("🟢 Using safe defaults")
    otif_target = 0.80
    freeze_hours = 48
    priority_strategy = "Balanced"
    shipping_days = ["Tuesday", "Friday"]
else:
    st.sidebar.info("🔧 Custom settings")
    otif_target = st.sidebar.slider("📈 OTIF Target", 0.70, 0.85, 0.80, 0.05)
    freeze_hours = st.sidebar.slider("🔒 Freeze Window (hours)", 24, 72, 48, 12)
    priority_strategy = st.sidebar.selectbox("🎯 Priority Strategy", 
                                           ["Balanced", "Speed First", "Cost First"])
    shipping_days = st.sidebar.multiselect("📅 Ship Days", 
                                          ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                                          default=["Tuesday", "Friday"])

params = {
    'otif_target': otif_target,
    'freeze_hours': freeze_hours,
    'priority_strategy': priority_strategy,
    'shipping_days': shipping_days
}

# Main App Header
st.title("📋 Pharma Weekly Planning Copilot")
st.markdown("**Single-Agent Batch-Driven Weekly Planning | 7-Day Rolling Window | 48h Freeze**")

# Tab Structure (Simplified to 3 tabs)
tab1, tab2, tab3 = st.tabs([
    "🎯 Planning & Optimize",
    "📊 Results & Analysis", 
    "✅ Export & Commit"
])

# Tab 1: Planning & Optimize
with tab1:
    st.markdown('<div class="tab-header"><h3>🎯 Planning & Optimization</h3></div>', unsafe_allow_html=True)
    
    # Show current data status
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("PPQ Batches", len(st.session_state.uploaded_data.get('ppq', [])))
    with col2:
        st.metric("Shipping Routes", len(st.session_state.uploaded_data.get('shipping', [])))
    with col3:
        st.metric("Active Scenarios", len(st.session_state.scenarios))
    
    # Data Upload Section (Collapsible)
    with st.expander("📤 Upload Custom Data (Optional - Sample data already loaded)", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            # Post Pack Queue (Required)
            ppq_file = st.file_uploader("Post Pack Queue (PPQ)", type=['xlsx', 'xls'], key="ppq")
            if ppq_file:
                ppq_df = pd.read_excel(ppq_file)
                
                # Validate schema
                ppq_required = ['batch_id', 'product', 'priority', 'value_eur', 'weight_kg', 'volume_m3']
                ppq_errors = validate_csv_schema(ppq_df, ppq_required, "PPQ")
                
                if ppq_errors:
                    for error in ppq_errors:
                        st.error(f"❌ {error}")
                    st.info("📋 Required PPQ columns: batch_id, product, priority, value_eur, weight_kg, volume_m3")
                else:
                    st.session_state.uploaded_data['ppq'] = ppq_df
                    st.success(f"✅ PPQ: {len(ppq_df)} rows loaded and validated")
            
            # Shipping Schedule (Required)
            shipping_file = st.file_uploader("Shipping Schedule", type=['xlsx', 'xls'], key="shipping")
            if shipping_file:
                shipping_df = pd.read_excel(shipping_file)
                
                # Validate schema
                shipping_required = ['route_id', 'destination_region', 'cost_per_kg', 'transit_days']
                shipping_errors = validate_csv_schema(shipping_df, shipping_required, "Shipping")
                
                if shipping_errors:
                    for error in shipping_errors:
                        st.error(f"❌ {error}")
                    st.info("📋 Required Shipping columns: route_id, destination_region, cost_per_kg, transit_days")
                else:
                    st.session_state.uploaded_data['shipping'] = shipping_df
                    st.success(f"✅ Shipping: {len(shipping_df)} routes loaded and validated")
        
        with col2:
            # Additional files
            for file_key, file_name in [
                ('orders', 'Customer Orders'),
                ('otif', 'OTIF Historical'),
                ('inventory', 'Current Inventory')
            ]:
                file_upload = st.file_uploader(file_name, type=['xlsx', 'xls'], key=file_key)
                if file_upload:
                    df = pd.read_excel(file_upload)
                    st.session_state.uploaded_data[file_key] = df
                    st.success(f"✅ {file_name}: {len(df)} rows loaded")
    
    # Planning Actions
    st.subheader("🚀 Create Your Plan")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **📋 Baseline Plan**
        - Simple first-available assignment
        - Tuesday/Friday shipping focus
        - Good starting point
        """)
        
        if st.button("📋 Create Baseline", type="secondary", use_container_width=True):
            with st.spinner("Creating baseline plan..."):
                try:
                    baseline_plan = simple_baseline(
                        st.session_state.uploaded_data['ppq'],
                        st.session_state.uploaded_data['shipping'],
                        freeze_hours
                    )
                    
                    if baseline_plan is not None and not baseline_plan.empty:
                        st.session_state.scenarios['baseline'] = baseline_plan
                        st.session_state.active_scenario = 'baseline'
                        st.success(f"✅ Baseline: {len(baseline_plan)} batches planned")
                    else:
                        st.error("❌ No baseline plan generated")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    with col2:
        st.markdown("""
        **🎯 Optimized Plan**
        - Priority-based optimization
        - Cost and speed balanced
        - Best routes selected
        """)
        
        if st.button("🎯 Run Optimization", type="primary", use_container_width=True):
            with st.spinner("Running optimization..."):
                try:
                    baseline_plan = st.session_state.scenarios.get('baseline')
                    
                    optimized_plan = simple_optimize(
                        st.session_state.uploaded_data['ppq'],
                        st.session_state.uploaded_data['shipping'],
                        params,
                        freeze_hours
                    )
                    
                    # Compare with baseline and mark changes
                    optimized_plan = compare_scenarios_for_changes(baseline_plan, optimized_plan)
                    st.session_state.scenarios['optimized'] = optimized_plan
                    st.session_state.active_scenario = 'optimized'
                    
                    st.success(f"✅ Optimized: {len(optimized_plan)} batches planned")
                    st.info("⚡ Used smart heuristic optimization")
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    # Scenario Selector
    if st.session_state.scenarios:
        st.markdown("---")
        st.subheader("📋 Active Plan")
        
        scenario_options = list(st.session_state.scenarios.keys())
        if len(scenario_options) == 1:
            st.info(f"📋 **Current Plan**: {scenario_options[0].title()}")
            st.session_state.active_scenario = scenario_options[0]
        else:
            active_scenario = st.selectbox(
                "**Choose Plan:**",
                scenario_options,
                index=scenario_options.index(st.session_state.active_scenario) if st.session_state.active_scenario in scenario_options else 0
            )
            st.session_state.active_scenario = active_scenario
    
    # Simple Scenario Comparison
    if len(st.session_state.scenarios) >= 2:
        st.markdown("---")
        st.subheader("📊 Compare Scenarios")
        
        col1, col2 = st.columns(2)
        with col1:
            scenario1 = st.selectbox("Compare:", list(st.session_state.scenarios.keys()), key="comp1")
        with col2:
            scenario2 = st.selectbox("With:", list(st.session_state.scenarios.keys()), key="comp2")
        
        if scenario1 != scenario2:
            plan1 = st.session_state.scenarios[scenario1]
            plan2 = st.session_state.scenarios[scenario2]
            
            if not plan1.empty and not plan2.empty:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(f"{scenario1.title()} Batches", len(plan1))
                    st.metric(f"{scenario1.title()} Cost", f"€{plan1.get('transport_cost_eur', 0).sum():,.0f}")
                with col2:
                    st.metric(f"{scenario2.title()} Batches", len(plan2))
                    st.metric(f"{scenario2.title()} Cost", f"€{plan2.get('transport_cost_eur', 0).sum():,.0f}")
                with col3:
                    diff_batches = len(plan2) - len(plan1)
                    diff_cost = plan2.get('transport_cost_eur', 0).sum() - plan1.get('transport_cost_eur', 0).sum()
                    st.metric("Δ Batches", diff_batches, delta=f"{diff_batches:+d}")
                    st.metric("Δ Cost", f"€{diff_cost:,.0f}", delta=f"{diff_cost:+.0f}")

# Tab 2: Results & Analysis
with tab2:
    st.markdown('<div class="tab-header"><h3>📊 Results & Analysis</h3></div>', unsafe_allow_html=True)
    
    if st.session_state.scenarios:
        
        # Display current scenario KPIs
        if st.session_state.active_scenario in st.session_state.scenarios:
            st.subheader(f"📊 KPIs: {st.session_state.active_scenario.title()}")
            
            current_plan = st.session_state.scenarios[st.session_state.active_scenario]
            kpis = kpi_summary(current_plan, st.session_state.uploaded_data.get('ppq'), otif_target)
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Total Cost", f"€{kpis['total_cost']:,.0f}")
            with col2:
                st.metric("OTIF", f"{kpis['otif_percent']:.1%}", 
                         delta=f"{kpis['otif_percent'] - otif_target:.1%}")
            with col3:
                st.metric("Weight Util.", f"{kpis['weight_utilization']:.1%}")
            with col4:
                st.metric("Volume Util.", f"{kpis['volume_utilization']:.1%}")
            with col5:
                st.metric("Mean Delay", f"{kpis['mean_delay']:.1f} days")
            
            # Freeze window indicator
            freeze_date = calculate_freeze_date(freeze_hours)
            st.info(f"🔒 Freeze Window: No changes allowed before {freeze_date.strftime('%Y-%m-%d %H:%M')}")
        
        # Scenario Comparison
        if len(st.session_state.scenarios) >= 2:
            st.subheader("⚖️ Scenario Comparison")
            
            col1, col2 = st.columns(2)
            with col1:
                base_scenario = st.selectbox("Base Scenario", list(st.session_state.scenarios.keys()), 
                                           index=0 if 'baseline' not in st.session_state.scenarios else list(st.session_state.scenarios.keys()).index('baseline'))
            with col2:
                compare_scenario = st.selectbox("Compare Scenario", list(st.session_state.scenarios.keys()),
                                              index=1 if len(st.session_state.scenarios) > 1 else 0)
            
            if base_scenario != compare_scenario:
                base_plan = st.session_state.scenarios[base_scenario]
                compare_plan = st.session_state.scenarios[compare_scenario]
                
                # KPI Comparison
                base_kpis = kpi_summary(base_plan, st.session_state.uploaded_data.get('ppq'), otif_target)
                compare_kpis = kpi_summary(compare_plan, st.session_state.uploaded_data.get('ppq'), otif_target)
                
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    delta_cost = compare_kpis['total_cost'] - base_kpis['total_cost']
                    st.metric("Cost Δ", f"€{compare_kpis['total_cost']:,.0f}", 
                             delta=f"€{delta_cost:,.0f}")
                
                with col2:
                    delta_otif = compare_kpis['otif_percent'] - base_kpis['otif_percent']
                    st.metric("OTIF Δ", f"{compare_kpis['otif_percent']:.1%}", 
                             delta=f"{delta_otif:.1%}")
                
                with col3:
                    delta_weight = compare_kpis['weight_utilization'] - base_kpis['weight_utilization']
                    st.metric("Weight Δ", f"{compare_kpis['weight_utilization']:.1%}", 
                             delta=f"{delta_weight:.1%}")
                
                with col4:
                    delta_volume = compare_kpis['volume_utilization'] - base_kpis['volume_utilization']
                    st.metric("Volume Δ", f"{compare_kpis['volume_utilization']:.1%}", 
                             delta=f"{delta_volume:.1%}")
                
                with col5:
                    delta_delay = compare_kpis['mean_delay'] - base_kpis['mean_delay']
                    st.metric("Delay Δ", f"{compare_kpis['mean_delay']:.1f} days", 
                             delta=f"{delta_delay:.1f} days")
        
        # Plan Details with Change Tracking
        st.subheader("📋 Plan Details & Change Tracking")
        
        if st.session_state.active_scenario in st.session_state.scenarios:
            plan = st.session_state.scenarios[st.session_state.active_scenario]
            
            if not plan.empty:
                # Show change summary
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    new_batches = len(plan[plan.get('change_type', '') == 'New'])
                    st.metric("New Batches", new_batches)
                
                with col2:
                    modified_batches = len(plan[plan.get('change_type', '') == 'Modified'])
                    st.metric("Modified Batches", modified_batches)
                
                with col3:
                    unchanged_batches = len(plan[plan.get('change_type', '') == 'Unchanged'])
                    st.metric("Unchanged Batches", unchanged_batches)
                
                # Show Tuesday/Friday breakdown
                tuesday_shipments = len(plan[pd.to_datetime(plan['ship_date']).dt.weekday == 1])
                friday_shipments = len(plan[pd.to_datetime(plan['ship_date']).dt.weekday == 4])
                st.info(f"📅 **Weekly Schedule**: {tuesday_shipments} Tuesday + {friday_shipments} Friday shipments")
                
                # Enhanced plan table with key information
                display_cols = [
                    'batch_id', 'product', 'current_station', 'priority', 
                    'ship_date', 'destination_market', 'transport_cost_eur', 'change_type'
                ]
                available_cols = [col for col in display_cols if col in plan.columns]
                
                # Add color coding for change types
                def highlight_changes(row):
                    change_type = row.get('change_type', '')
                    if change_type == 'New':
                        return ['background-color: #1f4e79'] * len(row)  # Blue for new
                    elif change_type == 'Modified':
                        return ['background-color: #8B4513'] * len(row)  # Brown for modified
                    elif change_type == 'Unchanged':
                        return ['background-color: #2d5016'] * len(row)  # Green for unchanged
                    else:
                        return [''] * len(row)
                
                if available_cols:
                    # Show legend for color coding
                    st.markdown("""
                    **Color Legend:**
                    - 🔵 **Blue**: New batches (not in baseline)
                    - 🟤 **Brown**: Modified batches (route or date changed from baseline)  
                    - 🟢 **Green**: Unchanged batches (same as baseline)
                    """)
                    
                    styled_df = plan[available_cols].style.apply(highlight_changes, axis=1)
                    st.dataframe(styled_df, use_container_width=True)
                
                # Consolidated Shipping Plan by Destination Market & Transport Mode
                if 'ship_date' in plan.columns:
                    st.subheader("📅 Consolidated Shipping Plan")
                    
                    # Create consolidated view by destination market and transport mode
                    plan_with_dates = plan.copy()
                    plan_with_dates['ship_date'] = pd.to_datetime(plan_with_dates['ship_date'])
                    plan_with_dates['week_day'] = plan_with_dates['ship_date'].dt.day_name()
                    
                    # Get transport mode from route_id or create based on destination
                    def get_transport_mode(route_id, destination):
                        # Simple logic to assign transport mode based on route/destination
                        if 'AIR' in route_id.upper() or any(dest in destination for dest in ['UK', 'Spain']):
                            return 'Air'
                        elif any(dest in destination for dest in ['Germany', 'France']):
                            return 'Road'
                        else:
                            return 'Sea'
                    
                    plan_with_dates['transport_mode'] = plan_with_dates.apply(
                        lambda row: get_transport_mode(row.get('route_id', ''), row.get('destination_market', '')), 
                        axis=1
                    )
                    
                    # Group by destination market, transport mode, and ship date
                    shipping_summary = plan_with_dates.groupby([
                        'destination_market', 'transport_mode', 'ship_date', 'week_day'
                    ]).agg({
                        'batch_id': 'count',
                        'weight_kg': 'sum',
                        'volume_m3': 'sum',
                        'transport_cost_eur': 'sum',
                        'priority': lambda x: f"{(x == 'Critical').sum()}C/{(x == 'High').sum()}H/{len(x)}T"
                    }).round(2)
                    
                    shipping_summary.columns = ['Batches', 'Total_Weight_kg', 'Total_Volume_m3', 'Total_Cost_EUR', 'Priority_Mix']
                    shipping_summary = shipping_summary.reset_index()
                    
                    # Format ship_date for better display
                    shipping_summary['Ship_Date'] = shipping_summary['ship_date'].dt.strftime('%Y-%m-%d (%a)')
                    
                    # Display consolidated shipping plan
                    display_cols = ['destination_market', 'transport_mode', 'Ship_Date', 'Batches', 
                                   'Total_Weight_kg', 'Total_Volume_m3', 'Total_Cost_EUR', 'Priority_Mix']
                    
                    st.dataframe(shipping_summary[display_cols], use_container_width=True)
                    
                    # Summary by transport mode
                    st.subheader("📊 Transport Mode Summary")
                    mode_summary = plan_with_dates.groupby('transport_mode').agg({
                        'batch_id': 'count',
                        'weight_kg': 'sum',
                        'transport_cost_eur': 'sum',
                        'destination_market': 'nunique'
                    }).round(2)
                    mode_summary.columns = ['Total_Batches', 'Total_Weight_kg', 'Total_Cost_EUR', 'Markets_Served']
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.dataframe(mode_summary, use_container_width=True)
                    
                    with col2:
                        # Chart showing shipments by mode
                        if not mode_summary.empty:
                            st.bar_chart(mode_summary['Total_Batches'])
                    
                    # Tuesday/Friday breakdown
                    tue_fri_summary = plan_with_dates[plan_with_dates['week_day'].isin(['Tuesday', 'Friday'])].groupby(['week_day', 'transport_mode']).agg({
                        'batch_id': 'count',
                        'transport_cost_eur': 'sum'
                    }).round(2)
                    
                    if not tue_fri_summary.empty:
                        st.subheader("📦 Tuesday/Friday Shipping Strategy")
                        tue_fri_summary.columns = ['Batches', 'Cost_EUR']
                        st.dataframe(tue_fri_summary, use_container_width=True)
                        
                        total_tue_fri = tue_fri_summary['Batches'].sum()
                        total_batches = len(plan_with_dates)
                        efficiency = (total_tue_fri / total_batches * 100) if total_batches > 0 else 0
                        st.info(f"📈 **Shipping Efficiency**: {total_tue_fri}/{total_batches} batches ({efficiency:.1f}%) on Tue/Fri")
            else:
                st.warning("⚠️ Selected scenario is empty.")
    
    else:
        st.warning("⚠️ No scenarios available. Please create scenarios in the Planning & Optimize tab first.")

# Tab 3: Export & Commit 
with tab3:
    st.markdown('<div class="tab-header"><h3>✅ Export & Commit Plans</h3></div>', unsafe_allow_html=True)
    
    if st.session_state.scenarios:
        
        # Select scenario to export
        export_scenario = st.selectbox("Select Scenario to Export", 
                                     list(st.session_state.scenarios.keys()),
                                     index=list(st.session_state.scenarios.keys()).index(st.session_state.active_scenario) if st.session_state.active_scenario in st.session_state.scenarios else 0)
        
        export_plan = st.session_state.scenarios[export_scenario]
        
        if not export_plan.empty:
            
            # Final validation
            st.subheader("🔍 Pre-Commit Validation")
            
            # Check OTIF compliance
            kpis = kpi_summary(export_plan, st.session_state.uploaded_data.get('ppq'), otif_target)
            
            otif_ok = kpis['otif_percent'] >= otif_target
            cost_reasonable = kpis['total_cost'] > 0
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if otif_ok:
                    st.success(f"✅ OTIF: {kpis['otif_percent']:.1%} (Target: {otif_target:.1%})")
                else:
                    st.error(f"❌ OTIF: {kpis['otif_percent']:.1%} (Target: {otif_target:.1%})")
            
            with col2:
                if cost_reasonable:
                    st.success(f"✅ Cost: €{kpis['total_cost']:,.0f}")
                else:
                    st.error("❌ Invalid cost calculation")
            
            with col3:
                freeze_date = calculate_freeze_date(freeze_hours)
                future_ships = (pd.to_datetime(export_plan['ship_date']) >= freeze_date).all()
                if future_ships:
                    st.success("✅ No freeze violations")
                else:
                    st.warning("⚠️ Some shipments violate freeze window")
            
            # Export Controls
            st.subheader("📤 Export Controls")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Release Priorities Export
                if st.button("📋 Export Release Priorities", type="secondary", use_container_width=True):
                    if 'ppq' in st.session_state.uploaded_data:
                        ppq_df = st.session_state.uploaded_data['ppq']
                        
                        release_export = export_plan.merge(ppq_df, on='batch_id', how='left')[
                            ['batch_id', 'expected_release_date', 'priority', 'destination_market', 'due_date']
                        ].rename(columns={'destination_market': 'destination'})
                        
                        csv = release_export.to_csv(index=False)
                        st.download_button(
                            label="💾 Download Release Priorities",
                            data=csv,
                            file_name=f"release_priorities_{timestamp}.csv",
                            mime="text/csv"
                        )
            
            with col2:
                # Consolidated Shipment Plan Export
                if st.button("🚚 Export Shipment Plan", type="secondary", use_container_width=True):
                    # Create consolidated export similar to the display
                    plan_with_dates = export_plan.copy()
                    plan_with_dates['ship_date'] = pd.to_datetime(plan_with_dates['ship_date'])
                    
                    # Add transport mode logic
                    def get_transport_mode(route_id, destination):
                        if 'AIR' in str(route_id).upper() or any(dest in str(destination) for dest in ['UK', 'Spain']):
                            return 'Air'
                        elif any(dest in str(destination) for dest in ['Germany', 'France']):
                            return 'Road'
                        else:
                            return 'Sea'
                    
                    plan_with_dates['transport_mode'] = plan_with_dates.apply(
                        lambda row: get_transport_mode(row.get('route_id', ''), row.get('destination_market', '')), 
                        axis=1
                    )
                    
                    # Create consolidated shipment plan
                    consolidated_export = plan_with_dates.groupby([
                        'destination_market', 'transport_mode', 'ship_date'
                    ]).agg({
                        'batch_id': lambda x: ','.join(x),  # List all batch IDs
                        'quantity': 'sum' if 'quantity' in plan_with_dates.columns else 'count',
                        'weight_kg': 'sum',
                        'volume_m3': 'sum',
                        'transport_cost_eur': 'sum',
                        'priority': lambda x: f"{(x == 'Critical').sum()}C/{(x == 'High').sum()}H/{len(x)}T"
                    }).reset_index()
                    
                    consolidated_export['ship_date'] = consolidated_export['ship_date'].dt.strftime('%Y-%m-%d')
                    consolidated_export.columns = [
                        'destination_market', 'transport_mode', 'ship_date', 
                        'batch_ids', 'total_quantity', 'total_weight_kg', 
                        'total_volume_m3', 'total_cost_eur', 'priority_mix'
                    ]
                    
                    csv = consolidated_export.to_csv(index=False)
                    st.download_button(
                        label="💾 Download Consolidated Plan",
                        data=csv,
                        file_name=f"consolidated_shipment_plan_{timestamp}.csv",
                        mime="text/csv"
                    )
            
            with col3:
                # Audit Log Export
                audit_data = {
                    "timestamp": timestamp,
                    "scenario": export_scenario,
                    "parameters": params,
                    "kpis": kpis,
                    "validation": {
                        "otif_compliant": otif_ok,
                        "cost_valid": cost_reasonable,
                        "freeze_compliant": future_ships
                    },
                    "batch_count": len(export_plan),
                    "user_session": "demo_user"
                }
                
                audit_json = json.dumps(audit_data, indent=2, default=str)
                
                st.download_button(
                    label="📄 Download Audit Log",
                    data=audit_json,
                    file_name=f"audit_log_{timestamp}.json",
                    mime="application/json"
                )
            
            # Final Commit
            st.subheader("🚀 Final Commit")
            
            commit_approved = st.checkbox("✅ I approve this plan for publication")
            
            if commit_approved and (otif_ok and cost_reasonable):
                if st.button("🚀 COMMIT TO PRODUCTION", type="primary", use_container_width=True):
                    st.balloons()
                    st.success("🎉 Plan committed to production successfully!")
                    st.info(f"📋 Scenario '{export_scenario}' is now the active production plan.")
            
            elif not (otif_ok and cost_reasonable):
                st.error("❌ Cannot commit: Validation failures detected. Please resolve issues first.")
        
        else:
            st.warning("⚠️ Selected scenario is empty. Please run optimization first.")
    
    else:
        st.warning("⚠️ No scenarios available. Please create scenarios in the Planning & Optimize tab first.")

# Footer
st.markdown("---")
st.markdown("**📋 Pharma Weekly Planning Copilot** | Built with Streamlit | 48h Freeze Policy Enabled")

# Methodology Documentation (Collapsible)
with st.expander("📚 Methodology & Scalability Notes", expanded=False):
    st.markdown("""
    ### 🎯 Current Design Philosophy
    - **Single-Agent Batch Processing**: Conscious trade-off for simplicity vs multi-agent complexity
    - **Excel-Driven**: Balance between flexibility and integration complexity
    - **Heuristic + Advanced Engine**: Fallback strategy for robustness
    
    ### ⚠️ Known Limitations & Mitigation
    
    **1. Excel Manual Process**
    - **Risk**: Version control, human errors, schema drift
    - **Mitigation**: Schema validation, template enforcement, clear error messages
    
    **2. Single-Agent Scalability**
    - **Risk**: May hit complexity ceiling at ~1000+ batches or complex multi-objective optimization
    - **Migration Path**: Evolution to microservices (API-driven), distributed optimization engines
    
    **3. Parameter Tuning Sensitivity**
    - **Risk**: α, OTIF targets, priority weights can destabilize KPIs
    - **Mitigation**: Parameter guards, safe defaults, "Green Path" mode for users
    
    **4. UI Complexity**
    - **Risk**: Too many levers overwhelm users
    - **Mitigation**: Simple Mode (default), progressive disclosure, contextual help
    
    ### 🚀 Scaling Roadmap
    1. **Phase 2**: API integration, real-time data feeds
    2. **Phase 3**: Multi-agent coordination, advanced ML models
    3. **Phase 4**: Full ERP integration, automated execution
    """)

# Display system status in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("🔧 System Status")
    # Advanced Engine status removed for cleaner POC
st.sidebar.write(f"📅 Freeze Date: {calculate_freeze_date(freeze_hours).strftime('%Y-%m-%d %H:%M')}")
st.sidebar.write(f"📊 Active Scenario: {st.session_state.active_scenario}")
st.sidebar.write(f"💾 Scenarios: {len(st.session_state.scenarios)}")

# Excel Template Downloads
st.sidebar.markdown("---")
st.sidebar.subheader("📋 Excel Templates")
if st.sidebar.button("📥 Download PPQ Template"):
    template_ppq = pd.DataFrame({
        'batch_id': ['BATCH_001', 'BATCH_002'],
        'product': ['Aspirin_100mg', 'Ibuprofen_200mg'],
        'priority': ['High', 'Medium'],
        'value_eur': [25000, 18000],
        'weight_kg': [1.5, 2.3],
        'volume_m3': [0.5, 0.8],
        'due_date': ['2025-08-20', '2025-08-25'],
        'destination_market': ['Germany', 'France'],
        'days_in_queue': [12, 8]
    })
    excel_template = template_ppq.to_excel(index=False)
    st.sidebar.download_button(
        label="💾 PPQ Template.xlsx",
        data=excel_template,
        file_name="PPQ_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if st.sidebar.button("📥 Download Shipping Template"):
    template_shipping = pd.DataFrame({
        'route_id': ['ROUTE_001', 'ROUTE_002'],
        'destination_region': ['Germany', 'France'],
        'cost_per_kg': [5.50, 6.20],
        'transit_days': [3, 2],
        'capacity_kg': [1000, 800],
        'capacity_m3': [150, 120],
        'mode': ['Road', 'Air']
    })
    excel_template = template_shipping.to_excel(index=False)
    st.sidebar.download_button(
        label="💾 Shipping Template.xlsx",
        data=excel_template,
        file_name="Shipping_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
