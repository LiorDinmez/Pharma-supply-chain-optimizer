"""
Pharmaceutical Supply Chain Optimizer - Simple Working Version
==============================================================
Basic version to test deployment and then enhance step by step.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="🏭 Pharma Supply Chain Optimizer",
    page_icon="🏭",
    layout="wide"
)

# Header
st.title("🏭 Pharmaceutical Supply Chain Optimizer")
st.markdown("**Advanced optimization engine for pharmaceutical supply chain management**")

# Check if sample data exists
try:
    # Try to load sample data
    batches_df = pd.read_csv('sample_data/sample_batches.csv')
    routes_df = pd.read_csv('sample_data/sample_routes.csv')
    data_loaded = True
except:
    data_loaded = False

if data_loaded:
    st.success("✅ Sample data loaded successfully!")
    
    # Display data overview
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Batch Data Overview")
        st.write(f"Total Batches: {len(batches_df)}")
        st.write(f"Total Value: €{batches_df['value_eur'].sum():,.0f}")
        st.write(f"Average Queue Time: {batches_df['days_in_queue'].mean():.1f} days")
        
        # Show batch data
        st.dataframe(batches_df.head(), use_container_width=True)
    
    with col2:
        st.subheader("🚚 Route Data Overview")
        st.write(f"Total Routes: {len(routes_df)}")
        st.write(f"Transport Modes: {', '.join(routes_df['transport_mode'].unique())}")
        
        # Show route data
        st.dataframe(routes_df.head(), use_container_width=True)
    
    # Simple optimization simulation
    st.subheader("🚀 Optimization Engine")
    
    if st.button("Run Basic Optimization", type="primary"):
        # Simulate optimization
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i in range(100):
            progress_bar.progress(i + 1)
            status_text.text(f'Optimizing... {i+1}%')
            if i % 20 == 0:
                st.sleep(0.1)
        
        status_text.text('Optimization Complete!')
        
        # Show mock results
        st.balloons()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Cost Reduction", "12.3%", "€45,230 saved")
        
        with col2:
            st.metric("Container Utilization", "89.4%", "4.2% increase")
        
        with col3:
            st.metric("OTIF Score", "91.7%", "Above target")
        
        with col4:
            st.metric("Risk Score", "23.1/100", "Low risk")
        
        st.success("🎉 Optimization completed successfully!")
        
        # Simple chart with basic matplotlib if plotly fails
        try:
            import plotly.express as px
            # Create a simple chart
            sample_data = pd.DataFrame({
                'Container': [f'CONT_{i:03d}' for i in range(1, 11)],
                'Utilization': np.random.uniform(70, 95, 10),
                'Cost': np.random.uniform(1000, 5000, 10)
            })
            
            fig = px.bar(sample_data, x='Container', y='Utilization', 
                        title='Container Utilization Results')
            st.plotly_chart(fig, use_container_width=True)
            
        except ImportError:
            # Fallback to simple table
            st.subheader("📊 Optimization Results")
            results_data = pd.DataFrame({
                'Container ID': [f'CONT_{i:03d}' for i in range(1, 6)],
                'Transport Mode': ['Air_Express', 'Ground_Standard', 'Ocean_Standard', 'Air_Standard', 'Ground_Express'],
                'Utilization (%)': [89.2, 92.1, 85.7, 88.9, 91.3],
                'Cost (EUR)': [2340, 1850, 3200, 2100, 1950]
            })
            st.dataframe(results_data, use_container_width=True)

else:
    st.error("❌ Sample data not found. Please check if sample_data/ folder exists with CSV files.")
    
    st.info("""
    **Expected files:**
    - `sample_data/sample_batches.csv`
    - `sample_data/sample_routes.csv`
    
    **Next Steps:**
    1. Check if the sample_data folder exists
    2. Verify CSV files are properly formatted
    3. Update requirements.txt with all dependencies
    """)

# Sidebar with information
with st.sidebar:
    st.header("ℹ️ System Status")
    
    # Check dependencies
    dependencies = {
        'pandas': True,
        'numpy': True,
        'streamlit': True
    }
    
    try:
        import plotly
        dependencies['plotly'] = True
    except ImportError:
        dependencies['plotly'] = False
    
    try:
        import ortools
        dependencies['ortools'] = True
    except ImportError:
        dependencies['ortools'] = False
    
    for dep, status in dependencies.items():
        if status:
            st.success(f"✅ {dep}")
        else:
            st.error(f"❌ {dep}")
    
    st.markdown("---")
    st.markdown("**📚 Documentation**")
    st.markdown("- [GitHub Repository](https://github.com/yourusername/pharma-supply-chain-optimizer)")
    st.markdown("- [User Guide](#)")
    st.markdown("- [API Documentation](#)")

# Footer
st.markdown("---")
st.markdown("**Built with ❤️ for pharmaceutical supply chain optimization**")
