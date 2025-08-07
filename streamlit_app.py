"""
Pharmaceutical Supply Chain Optimization Dashboard
=================================================
Clean, working Streamlit interface for your AdvancedOptimizationEngine
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time

# Import your optimization service
try:
    from optimization import get_optimization_service
    OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    st.error(f"Cannot import optimization service: {e}")
    OPTIMIZATION_AVAILABLE = False

# Import Plotly with fallback
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="🏭 Pharma Supply Chain Optimizer",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    
    .success-box {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .warning-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .info-box {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application"""
    
    # Header
    st.markdown('<div class="main-header">🏭 Pharmaceutical Supply Chain Optimizer</div>', unsafe_allow_html=True)
    
    st.markdown("""
    **Advanced optimization engine** for pharmaceutical supply chain management with:
    - 🎯 Multi-objective optimization (Cost vs Priority vs Transit Time)
    - 📊 Monte Carlo risk assessment with 2000+ iterations  
    - 🚚 Dual capacity constraints (Weight & Volume)
    - 📈 OTIF compliance monitoring
    - 💾 Persistent KPI tracking
    """)
    
    if not OPTIMIZATION_AVAILABLE:
        st.error("❌ Optimization engine not available. Please check your files.")
        return
    
    # Initialize service
    opt_service = get_optimization_service()
    
    # Sidebar configuration
    with st.sidebar:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   padding: 1.5rem; border-radius: 10px; margin-bottom: 2rem; color: white; text-align: center;">
            <h3 style="color: white; margin: 0;">⚙️ Control Panel</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Data source
        st.subheader("📂 Data Source")
        data_source = st.radio(
            "Choose data source:",
            ["🎯 Sample Data", "📄 Upload Files"]
        )
        
        # Optimization parameters
        st.subheader("🎛️ Parameters")
        
        alpha = st.slider(
            "Priority Weight (α)",
            min_value=0.001,
            max_value=0.1,
            value=0.01,
            step=0.001,
            help="Higher values prioritize delivery time over cost"
        )
        
        max_transit = st.slider(
            "Max Transit Days",
            min_value=7,
            max_value=30,
            value=21
        )
        
        min_otif = st.slider(
            "Target OTIF Rate",
            min_value=0.5,
            max_value=1.0,
            value=0.8,
            step=0.05,
            format="%.0%"
        )
        
        constraints = {
            'alpha': alpha,
            'max_transit_days': max_transit,
            'min_otif_rate': min_otif
        }
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["🚀 Optimization", "📊 Dashboard", "📈 History"])
    
    with tab1:
        optimization_tab(opt_service, data_source, constraints)
    
    with tab2:
        dashboard_tab(opt_service)
    
    with tab3:
        history_tab(opt_service)

def optimization_tab(opt_service, data_source, constraints):
    """Main optimization interface"""
    
    st.header("🚀 Supply Chain Optimization")
    
    # Load data
    try:
        if data_source == "🎯 Sample Data":
            with st.spinner("Loading sample data..."):
                batches_df, routes_df = opt_service.load_sample_data()
            
            st.markdown("""
            <div class="success-box">
                <h4 style="margin: 0 0 0.5rem 0;">✅ Sample Data Loaded Successfully!</h4>
                <p style="margin: 0; opacity: 0.9;">Realistic pharmaceutical batch and route data ready for optimization.</p>
            </div>
            """, unsafe_allow_html=True)
            
        else:
            st.subheader("📤 Upload Your Data")
            
            col1, col2 = st.columns(2)
            with col1:
                batch_file = st.file_uploader("Batch Data (CSV)", type=['csv'])
            with col2:
                route_file = st.file_uploader("Route Data (CSV)", type=['csv'])
            
            if batch_file and route_file:
                batches_df = pd.read_csv(batch_file)
                routes_df = pd.read_csv(route_file)
                st.success("✅ Files uploaded successfully!")
            else:
                st.info("Please upload both batch and route CSV files.")
                return
        
        # Validate data
        validation = opt_service.validate_data(batches_df, routes_df)
        
        if not validation['valid']:
            st.markdown('<div class="warning-box"><h4>❌ Data Validation Failed</h4></div>', unsafe_allow_html=True)
            for error in validation['errors']:
                st.error(f"• {error}")
            return
        
        # Display summary
        display_data_summary(validation['summary'])
        
        # Data preview
        with st.expander("📋 Data Preview"):
            preview_tab1, preview_tab2 = st.tabs(["Batch Data", "Route Data"])
            
            with preview_tab1:
                st.dataframe(batches_df.head(), use_container_width=True)
            
            with preview_tab2:
                st.dataframe(routes_df.head(), use_container_width=True)
        
        # Run optimization
        st.markdown("---")
        st.subheader("🎯 Execute Optimization")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("🚀 **OPTIMIZE SUPPLY CHAIN**", type="primary", use_container_width=True):
                run_optimization(opt_service, batches_df, routes_df, constraints)
        
        with col2:
            if st.button("📊 View Results", use_container_width=True):
                if 'optimization_results' in st.session_state:
                    st.info("Switch to Dashboard tab to view results")
                else:
                    st.warning("Run optimization first")
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.info("Check that your sample_data folder contains the CSV files")

def display_data_summary(summary):
    """Display data summary with metrics"""
    
    st.subheader("📊 Data Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Batches",
            f"{summary['total_batches']:,}",
            help="Number of pharmaceutical batches"
        )
    
    with col2:
        st.metric(
            "Total Value", 
            f"€{summary['total_value_eur']:,.0f}",
            help="Combined value of all batches"
        )
    
    with col3:
        st.metric(
            "Avg Queue Time",
            f"{summary['avg_days_in_queue']:.1f} days",
            help="Average days batches have been waiting"
        )
    
    with col4:
        st.metric(
            "Critical Batches",
            f"{summary['critical_batches']}",
            help="Batches requiring investigation"
        )
    
    # Transport modes
    modes = ", ".join(summary['available_transport_modes'])
    st.markdown(f"""
    <div class="info-box">
        <strong>🚚 Available Transport Modes:</strong> {modes}
    </div>
    """, unsafe_allow_html=True)

def run_optimization(opt_service, batches_df, routes_df, constraints):
    """Execute optimization with progress tracking"""
    
    progress_container = st.container()
    
    with progress_container:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   padding: 2rem; border-radius: 10px; color: white; text-align: center; margin: 1rem 0;">
            <h3 style="color: white; margin: 0;">🚀 Optimization Engine Running</h3>
        </div>
        """, unsafe_allow_html=True)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        steps = [
            "🔍 Validating input data...",
            "📊 Creating batch and route objects...",
            "🎯 Running OR-Tools optimization...", 
            "📦 Optimizing container packing...",
            "🚚 Calculating optimal routes...",
            "🎲 Monte Carlo risk assessment...",
            "📈 OTIF compliance validation...",
            "💾 Saving results and KPIs...",
            "✅ Optimization completed!"
        ]
        
        try:
            for i, step in enumerate(steps[:-1]):
                status_text.markdown(f"**{step}**")
                progress_bar.progress((i + 1) / len(steps))
                time.sleep(0.5)
            
            # Run actual optimization
            results = opt_service.run_optimization(batches_df, routes_df, constraints)
            
            # Final step
            status_text.markdown(f"**{steps[-1]}**")
            progress_bar.progress(1.0)
            
            # Store results
            st.session_state['optimization_results'] = results
            st.session_state['optimization_timestamp'] = datetime.now()
            
            # Clear progress
            progress_bar.empty()
            status_text.empty()
            
            st.balloons()
            
            st.markdown("""
            <div class="success-box">
                <h3 style="margin: 0 0 1rem 0;">🎉 Optimization Completed Successfully!</h3>
                <p style="margin: 0;">Advanced algorithms with Monte Carlo simulation have optimized your supply chain.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Display results
            display_optimization_results(results)
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Optimization failed: {str(e)}")

def display_optimization_results(results):
    """Display optimization results"""
    
    st.subheader("🎯 Optimization Results")
    
    kpis = results['kpis']
    risk = results['risk_analysis']
    otif = results['otif_compliance']
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        cost_reduction = (1 - kpis.get('cost_ratio', 1)) * 100
        st.metric(
            "Cost Reduction",
            f"{cost_reduction:.1f}%",
            f"€{kpis.get('total_cost_eur', 0):,.0f} total"
        )
    
    with col2:
        utilization = kpis.get('avg_container_utilization', 0) * 100
        st.metric(
            "Container Utilization",
            f"{utilization:.1f}%",
            "Efficiency improved"
        )
    
    with col3:
        otif_score = risk.get('otif_statistics', {}).get('mean', 0) * 100
        st.metric(
            "OTIF Score",
            f"{otif_score:.1f}%",
            "On-Time In-Full"
        )
    
    with col4:
        risk_score = risk.get('risk_score', 0)
        st.metric(
            "Risk Score",
            f"{risk_score:.1f}/100",
            "Lower is better"
        )
    
    # Shipment plan
    with st.expander("📋 Detailed Shipment Plan", expanded=True):
        plan_df = pd.DataFrame(results['optimized_plan'])
        if not plan_df.empty:
            st.dataframe(plan_df, use_container_width=True)
            
            # Export options
            col1, col2 = st.columns(2)
            
            with col1:
                csv_data = opt_service.export_results(results, 'csv')
                st.download_button(
                    "📥 Download CSV",
                    data=csv_data,
                    file_name=f"optimization_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                summary_data = opt_service.export_results(results, 'summary')
                st.download_button(
                    "📄 Download Summary",
                    data=summary_data,
                    file_name=f"optimization_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )

def dashboard_tab(opt_service):
    """Dashboard with visualizations"""
    
    st.header("📊 Analytics Dashboard")
    
    if 'optimization_results' not in st.session_state:
        st.markdown("""
        <div class="info-box">
            <h4 style="margin: 0 0 1rem 0;">🎯 Ready for Analytics</h4>
            <p style="margin: 0;">Run an optimization first to see advanced analytics and visualizations.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    results = st.session_state['optimization_results']
    timestamp = st.session_state.get('optimization_timestamp', datetime.now())
    
    st.info(f"📅 **Last optimization:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create visualizations
    if PLOTLY_AVAILABLE:
        create_plotly_charts(results)
    else:
        create_basic_charts(results)

def create_plotly_charts(results):
    """Create Plotly visualizations"""
    
    kpis = results['kpis']
    plan = results.get('optimized_plan', [])
    
    if not plan:
        st.warning("No plan data available for visualization")
        return
    
    plan_df = pd.DataFrame(plan)
    
    # Container utilization
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚛 Container Utilization")
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='Weight Utilization',
            x=plan_df['container_id'],
            y=plan_df['utilization_weight'] * 100,
            marker_color='rgba(102, 126, 234, 0.8)'
        ))
        fig.add_trace(go.Bar(
            name='Volume Utilization',
            x=plan_df['container_id'],
            y=plan_df['utilization_volume'] * 100,
            marker_color='rgba(255, 127, 14, 0.8)'
        ))
        
        fig.update_layout(
            xaxis_title="Container ID",
            yaxis_title="Utilization (%)",
            barmode='group',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🚚 Transport Mode Distribution")
        
        mode_counts = plan_df['transport_mode'].value_counts()
        fig = px.pie(
            values=mode_counts.values,
            names=mode_counts.index,
            title="Containers by Transport Mode"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Cost analysis
    st.subheader("💰 Cost Analysis")
    
    fig = px.scatter(
        plan_df,
        x='utilization_weight',
        y='route_cost_eur',
        size='num_batches',
        color='transport_mode',
        title='Cost vs Utilization Analysis'
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

def create_basic_charts(results):
    """Basic charts without Plotly"""
    
    plan = results.get('optimized_plan', [])
    if not plan:
        st.warning("No plan data available")
        return
    
    plan_df = pd.DataFrame(plan)
    
    st.subheader("📊 Container Performance")
    
    # Utilization chart
    chart_data = plan_df[['container_id', 'utilization_weight', 'utilization_volume']].set_index('container_id')
    chart_data = chart_data * 100  # Convert to percentage
    st.bar_chart(chart_data)
    
    # Transport mode breakdown
    st.subheader("🚚 Transport Mode Usage")
    mode_counts = plan_df['transport_mode'].value_counts()
    st.bar_chart(mode_counts)

def history_tab(opt_service):
    """Historical performance tracking"""
    
    st.header("📈 Optimization History")
    
    history_df = opt_service.get_optimization_history()
    
    if history_df.empty:
        st.markdown("""
        <div class="info-box">
            <h4 style="margin: 0 0 1rem 0;">📊 Performance Tracking</h4>
            <p style="margin: 0;">No optimization history yet. Run optimizations to see performance trends over time.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Display trends
    st.subheader("📊 Performance Trends")
    
    if PLOTLY_AVAILABLE:
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Total Cost', 'Cost Efficiency', 'Container Utilization', 'Cycle Time')
        )
        
        fig.add_trace(go.Scatter(
            x=history_df['run_number'], 
            y=history_df['total_cost'],
            mode='lines+markers',
            name='Total Cost'
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=history_df['run_number'], 
            y=history_df['cost_ratio']*100,
            mode='lines+markers', 
            name='Cost Efficiency'
        ), row=1, col=2)
        
        fig.add_trace(go.Scatter(
            x=history_df['run_number'], 
            y=history_df['container_util']*100,
            mode='lines+markers',
            name='Utilization'
        ), row=2, col=1)
        
        fig.add_trace(go.Scatter(
            x=history_df['run_number'], 
            y=history_df['cycle_improve']*100,
            mode='lines+markers',
            name='Cycle Time'
        ), row=2, col=2)
        
        fig.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.line_chart(history_df.set_index('run_number')[['total_cost', 'container_util']])
    
    # Recent runs
    st.subheader("📋 Recent Optimization Runs")
    
    for _, row in history_df.head(5).iterrows():
        with st.container():
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Run", f"#{row['run_number']}")
            with col2:
                st.metric("Cost", f"€{row['total_cost']:,.0f}")
            with col3:
                st.metric("Utilization", f"{row['container_util']*100:.1f}%")
            with col4:
                st.metric("Date", row['timestamp'].strftime('%m/%d'))
        st.markdown("---")

if __name__ == "__main__":
    main()
