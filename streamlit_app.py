# Streamlit Cloud Entry Point
# This file imports and runs the main dashboard

import streamlit as st
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set page config
st.set_page_config(
    page_title="Pharma Supply Chain POC",
    page_icon="🏭",
    layout="wide"
)

try:
    # Import the main dashboard
    from dashboard_pharma import main
    
    # Run the main function
    main()
    
except ImportError as e:
    st.error(f"❌ Import Error: {str(e)}")
    st.info("💡 Please check that all required files are present:")
    st.code("""
    Required files:
    - dashboard_pharma.py
    - optimization_engine_v2.py
    - batches_v2.csv
    - routes_v2.csv.csv
    """)
    
except Exception as e:
    st.error(f"❌ Application Error: {str(e)}")
    st.info("💡 Please check the logs for more details.") 
