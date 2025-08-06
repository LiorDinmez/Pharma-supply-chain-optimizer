"""
Advanced Dashboard Module for Pharmaceutical Supply Chain Optimization
====================================================================
This module provides sophisticated visualization capabilities for analyzing
optimization results, KPI trends, and supply chain performance metrics.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
import streamlit as st

class SupplyChainDashboard:
    """Advanced dashboard for supply chain optimization analytics"""
    
    def __init__(self):
        self.color_palette = {
            'primary': '#1f77b4',
            'secondary': '#ff7f0e', 
            'success': '#2ca02c',
            'warning': '#d62728',
            'info': '#9467bd',
            'light': '#17becf'
        }
    
    def create_executive_summary(self, results: Dict[str, Any]) -> go.Figure:
        """Create executive summary dashboard"""
        
        kpis = results.get('kpis', {})
        risk = results.get('risk_analysis', {})
        otif = results.get('otif_compliance', {})
        
        # Create subplot figure
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=(
                'Cost Performance', 'Operational Efficiency', 'Risk Profile',
                'OTIF Compliance', 'Container Utilization', 'Cycle Time Impact'
            ),
            specs=[
                [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}],
                [{"type": "indicator"}, {"type": "scatter"}, {"type": "bar"}]
            ],
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )
        
        # Cost Performance Gauge
        cost_reduction = (1 - kpis.get('cost_ratio', 1)) * 100
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=cost_reduction,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Cost Reduction (%)"},
            delta={'reference': 10},
            gauge={
                'axis': {'range': [None, 20]},
                'bar': {'color': self.color_palette['success']},
                'steps': [
                    {'range': [0, 5], 'color': "lightgray"},
                    {'range': [5, 15], 'color': "yellow"}
                ],
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 15}
            }
        ), row=1, col=1)
        
        # Operational Efficiency
        utilization = kpis.get('avg_container_utilization', 0) * 100
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=utilization,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Container Utilization (%)"},
            delta={'reference': 80},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': self.color_palette['primary']},
                'steps': [
                    {'range': [0, 60], 'color': "lightgray"},
                    {'range': [60, 85], 'color': "yellow"}
                ],
                'threshold': {'line': {'color': "green", 'width': 4}, 'thickness': 0.75, 'value': 85}
            }
        ), row=1, col=2)
        
        # Risk Profile
        risk_score = risk.get('risk_score', 0)
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=risk_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Risk Score (0-100)"},
            delta={'reference': 30, 'increasing': {'color': "red"}},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': self.color_palette['warning']},
                'steps': [
                    {'range': [0, 25], 'color': "lightgreen"},
                    {'range': [25, 50], 'color': "yellow"},
                    {'range': [50, 100], 'color': "lightcoral"}
                ],
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 50}
            }
        ), row=1, col=3)
        
        # OTIF Compliance
        otif_rate = otif.get('otif_rate', 0) * 100
        fig.add_trace(go.Indicator(
            mode="number+delta",
            value=otif_rate,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "OTIF Rate (%)"},
            delta={'reference': 80, 'valueformat': '.1f'},
            number={'valueformat': '.1f', 'suffix': '%'}
        ), row=2, col=1)
        
        fig.update_layout(
            height=800,
            title_text="Executive Performance Dashboard",
            title_x=0.5,
            font=dict(size=12)
        )
        
        return fig
    
    def create_route_analysis_chart(self, results: Dict[str, Any]) -> go.Figure:
        """Create detailed route analysis visualization"""
        
        plan = results.get('optimized_plan', [])
        if not plan:
            return go.Figure()
        
        plan_df = pd.DataFrame(plan)
        
        # Create bubble chart: cost vs utilization vs container count
        fig = px.scatter(
            plan_df,
            x='utilization_weight',
            y='route_cost_eur',
            size='num_batches',
            color='transport_mode',
            hover_data=['container_id', 'total_weight_kg', 'total_volume_m3'],
            title='Route Performance Analysis: Cost vs Utilization',
            labels={
                'utilization_weight': 'Weight Utilization (%)',
                'route_cost_eur': 'Route Cost (EUR)',
                'num_batches': 'Number of Batches'
            }
        )
        
        fig.update_traces(marker=dict(sizemode='area', sizeref=2.*max(plan_df['num_batches'])/(40.**2), line_width=2))
        fig.update_layout(height=600, showlegend=True)
        
        return fig
    
    def create_capacity_utilization_chart(self, results: Dict[str, Any]) -> go.Figure:
        """Create detailed capacity utilization analysis"""
        
        plan = results.get('optimized_plan', [])
        if not plan:
            return go.Figure()
        
        plan_df = pd.DataFrame(plan)
        
        # Calculate utilization percentages
        plan_df['weight_util_pct'] = plan_df['utilization_weight'] * 100
        plan_df['volume_util_pct'] = plan_df['utilization_volume'] * 100
        
        fig = go.Figure()
        
        # Weight utilization bars
        fig.add_trace(go.Bar(
            name='Weight Utilization',
            x=plan_df['container_id'],
            y=plan_df['weight_util_pct'],
            marker_color=self.color_palette['primary'],
            opacity=0.8,
            hovertemplate='Container: %{x}<br>Weight Util: %{y:.1f}%<br>Weight: %{customdata:.0f} kg',
            customdata=plan_df['total_weight_kg']
        ))
        
        # Volume utilization bars  
        fig.add_trace(go.Bar(
            name='Volume Utilization',
            x=plan_df['container_id'],
            y=plan_df['volume_util_pct'],
            marker_color=self.color_palette['secondary'],
            opacity=0.8,
            hovertemplate='Container: %{x}<br>Volume Util: %{y:.1f}%<br>Volume: %{customdata:.1f} m³',
            customdata=plan_df['total_volume_m3']
        ))
        
        # Add target utilization line
        fig.add_hline(y=85, line_dash="dash", line_color="green", 
                      annotation_text="Target: 85%")
        
        fig.update_layout(
            title='Container Utilization Analysis: Weight vs Volume',
            xaxis_title='Container ID',
            yaxis_title='Utilization (%)',
            barmode='group',
            height=500,
            hovermode='x unified'
        )
        
        return fig

def create_dashboard_page(results: Dict[str, Any], historical_data: pd.DataFrame = None):
    """Create comprehensive dashboard page for Streamlit"""
    
    dashboard = SupplyChainDashboard()
    
    st.title("📊 Advanced Analytics Dashboard")
    
    # Executive Summary
    st.subheader("🎯 Executive Summary")
    exec_fig = dashboard.create_executive_summary(results)
    st.plotly_chart(exec_fig, use_container_width=True)
    
    # Detailed Analysis Tabs
    tab1, tab2 = st.tabs(["🚛 Route Analysis", "📦 Capacity Analysis"])
    
    with tab1:
        st.subheader("Route Performance Analysis")
        route_fig = dashboard.create_route_analysis_chart(results)
        st.plotly_chart(route_fig, use_container_width=True)
    
    with tab2:
        st.subheader("Container Capacity Utilization")
        capacity_fig = dashboard.create_capacity_utilization_chart(results)
        st.plotly_chart(capacity_fig, use_container_width=True)
