"""
Pharmaceutical Supply Chain Optimization Dashboard - Enhanced Visual Edition
=========================================================================
Beautiful, colorful, and highly interactive Streamlit application for 
pharmaceutical supply chain optimization with stunning visualizations.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import time

# Try to import plotly with error handling
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.error("⚠️ Plotly not available. Please check requirements.txt")

# Try to import optimization service with error handling
try:
    from optimization import get_optimization_service
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False
    st.error("⚠️ Optimization module not available. Please check optimization.py")

class SupplyChainDashboard:
    """Advanced dashboard with beautiful, colorful visualizations"""
    
    def __init__(self):
        # Modern gradient color palette
        self.color_palette = {
            'primary': '#667eea',
            'secondary': '#764ba2', 
            'success': '#11998e',
            'success_light': '#38ef7d',
            'warning': '#f093fb',
            'warning_light': '#f5576c',
            'info': '#4facfe',
            'info_light': '#00f2fe',
            'accent1': '#ff9a9e',
            'accent2': '#fecfef',
            'accent3': '#a8edea',
            'accent4': '#fed6e3'
        }
        
        # Beautiful gradient combinations
        self.gradients = {
            'primary': ['#667eea', '#764ba2'],
            'success': ['#11998e', '#38ef7d'],
            'warning': ['#f093fb', '#f5576c'],
            'info': ['#4facfe', '#00f2fe'],
            'sunset': ['#ff9a9e', '#fecfef'],
            'ocean': ['#a8edea', '#fed6e3'],
            'royal': ['#667eea', '#764ba2'],
            'fire': ['#ff6b6b', '#ffa500']
        }
        
        # Enhanced color scales for different chart types
        self.color_scales = {
            'performance': ['#e74c3c', '#f39c12', '#f1c40f', '#2ecc71', '#27ae60'],
            'risk': ['#27ae60', '#f39c12', '#e67e22', '#e74c3c'],
            'efficiency': px.colors.sequential.Viridis_r,
            'cost': px.colors.sequential.Reds_r,
            'utilization': px.colors.sequential.Blues
        }
    
    def create_executive_summary(self, results: Dict[str, Any]) -> go.Figure:
        """Create stunning executive summary with modern gauges and gradients"""
        
        kpis = results.get('kpis', {})
        risk = results.get('risk_analysis', {})
        otif = results.get('otif_compliance', {})
        
        # Create sophisticated subplot layout
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=(
                '💰 Cost Performance', '📦 Operational Efficiency', '⚠️ Risk Profile',
                '🎯 OTIF Compliance', '📊 Container Utilization', '⚡ Cycle Time Impact'
            ),
            specs=[
                [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}],
                [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]
            ],
            vertical_spacing=0.15,
            horizontal_spacing=0.1
        )
        
        # Enhanced Cost Performance Gauge with gradient colors
        cost_reduction = (1 - kpis.get('cost_ratio', 1)) * 100
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=cost_reduction,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Cost Reduction (%)", 'font': {'size': 16, 'color': '#2c3e50'}},
            delta={'reference': 10, 'increasing': {'color': self.color_palette['success']}, 
                   'decreasing': {'color': self.color_palette['warning']}},
            number={'font': {'size': 28, 'color': '#2c3e50'}},
            gauge={
                'axis': {'range': [None, 20], 'tickcolor': "#34495e", 'tickwidth': 2},
                'bar': {'color': self.color_palette['primary'], 'thickness': 0.8},
                'steps': [
                    {'range': [0, 5], 'color': "#ecf0f1"},
                    {'range': [5, 10], 'color': "#f8f9fa"},
                    {'range': [10, 15], 'color': self.color_palette['accent3']},
                    {'range': [15, 20], 'color': self.color_palette['success']}
                ],
                'threshold': {
                    'line': {'color': self.color_palette['warning'], 'width': 4},
                    'thickness': 0.75,
                    'value': 15
                }
            }
        ), row=1, col=1)
        
        # Enhanced Operational Efficiency Gauge
        utilization = kpis.get('avg_container_utilization', 0) * 100
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=utilization,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Container Utilization (%)", 'font': {'size': 16, 'color': '#2c3e50'}},
            delta={'reference': 80, 'increasing': {'color': self.color_palette['success']}},
            number={'font': {'size': 28, 'color': '#2c3e50'}},
            gauge={
                'axis': {'range': [None, 100], 'tickcolor': "#34495e", 'tickwidth': 2},
                'bar': {'color': self.color_palette['info'], 'thickness': 0.8},
                'steps': [
                    {'range': [0, 60], 'color': "#ecf0f1"},
                    {'range': [60, 75], 'color': self.color_palette['accent4']},
                    {'range': [75, 85], 'color': self.color_palette['accent3']},
                    {'range': [85, 100], 'color': self.color_palette['success']}
                ],
                'threshold': {
                    'line': {'color': self.color_palette['success'], 'width': 4},
                    'thickness': 0.75,
                    'value': 85
                }
            }
        ), row=1, col=2)
        
        # Enhanced Risk Profile Gauge
        risk_score = risk.get('risk_score', 0)
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=risk_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Risk Score (0-100)", 'font': {'size': 16, 'color': '#2c3e50'}},
            delta={'reference': 30, 'increasing': {'color': self.color_palette['warning']}, 
                   'decreasing': {'color': self.color_palette['success']}},
            number={'font': {'size': 28, 'color': '#2c3e50'}},
            gauge={
                'axis': {'range': [None, 100], 'tickcolor': "#34495e", 'tickwidth': 2},
                'bar': {'color': self.color_palette['warning'], 'thickness': 0.8},
                'steps': [
                    {'range': [0, 25], 'color': self.color_palette['success_light']},
                    {'range': [25, 50], 'color': "#f1c40f"},
                    {'range': [50, 75], 'color': "#e67e22"},
                    {'range': [75, 100], 'color': self.color_palette['warning']}
                ],
                'threshold': {
                    'line': {'color': self.color_palette['warning'], 'width': 4},
                    'thickness': 0.75,
                    'value': 50
                }
            }
        ), row=1, col=3)
        
        # Enhanced OTIF Compliance
        otif_rate = otif.get('otif_rate', 0) * 100
        fig.add_trace(go.Indicator(
            mode="number+delta+gauge",
            value=otif_rate,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "OTIF Rate (%)", 'font': {'size': 16, 'color': '#2c3e50'}},
            delta={'reference': 80, 'valueformat': '.1f', 'increasing': {'color': self.color_palette['success']}},
            number={'valueformat': '.1f', 'suffix': '%', 'font': {'size': 28, 'color': '#2c3e50'}},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': self.color_palette['primary']},
                'steps': [{'range': [0, 80], 'color': "#ecf0f1"}, {'range': [80, 100], 'color': self.color_palette['success']}],
                'threshold': {'line': {'color': self.color_palette['success'], 'width': 4}, 'thickness': 0.75, 'value': 80}
            }
        ), row=2, col=1)
        
        # Container Count and Efficiency
        container_count = kpis.get('total_containers', 0)
        fig.add_trace(go.Indicator(
            mode="number+delta",
            value=container_count,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Total Containers", 'font': {'size': 16, 'color': '#2c3e50'}},
            number={'font': {'size': 28, 'color': self.color_palette['info']}}
        ), row=2, col=2)
        
        # Cycle Time Improvement
        cycle_improvement = kpis.get('cycle_time_improvement', 0) * 100
        fig.add_trace(go.Indicator(
            mode="number+delta",
            value=cycle_improvement,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Cycle Time Improvement (%)", 'font': {'size': 16, 'color': '#2c3e50'}},
            delta={'reference': 10, 'valueformat': '.1f'},
            number={'valueformat': '.1f', 'suffix': '%', 'font': {'size': 28, 'color': self.color_palette['accent1']}}
        ), row=2, col=3)
        
        fig.update_layout(
            height=800,
            title={
                'text': '🎯 Executive Performance Dashboard',
                'x': 0.5,
                'font': {'size': 24, 'color': '#2c3e50', 'family': 'Arial Black'}
            },
            font=dict(size=12, family="Arial"),
            template="plotly_white",
            margin=dict(l=40, r=40, t=80, b=40)
        )
        
        return fig
    
    def create_route_analysis_chart(self, results: Dict[str, Any]) -> go.Figure:
        """Create stunning route analysis with beautiful bubble chart"""
        
        plan = results.get('optimized_plan', [])
        if not plan:
            return self._create_empty_chart("No route data available")
        
        plan_df = pd.DataFrame(plan)
        
        # Enhanced bubble chart with gradient colors
        fig = px.scatter(
            plan_df,
            x='utilization_weight',
            y='route_cost_eur',
            size='num_batches',
            color='transport_mode',
            hover_data=['container_id', 'total_weight_kg', 'total_volume_m3'],
            title='🚚 Route Performance Analysis: Cost vs Utilization Efficiency',
            labels={
                'utilization_weight': 'Weight Utilization Efficiency (%)',
                'route_cost_eur': 'Route Cost (EUR)',
                'num_batches': 'Number of Batches',
                'transport_mode': 'Transport Mode'
            },
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        # Enhanced styling
        fig.update_traces(
            marker=dict(
                sizemode='area',
                sizeref=2.*max(plan_df['num_batches'])/(50.**2),
                line=dict(width=2, color='white'),
                opacity=0.8
            ),
            hovertemplate='<b>%{hovertext}</b><br>' +
                         'Container: %{customdata[0]}<br>' +
                         'Weight: %{customdata[1]:,.1f} kg<br>' +
                         'Volume: %{customdata[2]:.1f} m³<br>' +
                         'Cost: €%{y:,.2f}<br>' +
                         'Utilization: %{x:.1%}<br>' +
                         'Batches: %{marker.size}<extra></extra>'
        )
        
        fig.update_layout(
            height=600,
            showlegend=True,
            template="plotly_white",
            title_font_size=20,
            title_font_color='#2c3e50',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            ),
            xaxis=dict(tickformat='.0%', gridcolor='rgba(128,128,128,0.2)'),
            yaxis=dict(tickformat='€,.0f', gridcolor='rgba(128,128,128,0.2)')
        )
        
        return fig
    
    def create_risk_distribution_chart(self, risk_analysis: Dict[str, Any]) -> go.Figure:
        """Create beautiful risk distribution analysis with gradients"""
        
        otif_mean = risk_analysis.get('otif_statistics', {}).get('mean', 0.8)
        delay_mean = risk_analysis.get('delay_statistics', {}).get('mean_delay_days', 2.0)
        delay_p95 = risk_analysis.get('delay_statistics', {}).get('p95_delay_days', 5.0)
        
        # Generate enhanced distribution for visualization
        np.random.seed(42)
        otif_samples = np.random.beta(otif_mean * 10, (1 - otif_mean) * 10, 2000)
        delay_samples = np.random.gamma(2, delay_mean / 2, 2000)
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('🎯 OTIF Score Distribution', '⏱️ Delay Distribution (Days)'),
            horizontal_spacing=0.1
        )
        
        # Enhanced OTIF distribution with gradient
        fig.add_trace(go.Histogram(
            x=otif_samples * 100,
            nbinsx=30,
            name='OTIF Distribution',
            marker=dict(
                color=otif_samples * 100,
                colorscale=[[0, self.color_palette['warning']], 
                           [0.5, self.color_palette['accent3']], 
                           [1, self.color_palette['success']]],
                line=dict(color='white', width=1)
            ),
            opacity=0.8,
            hovertemplate='OTIF Range: %{x:.1f}%<br>Frequency: %{y}<extra></extra>'
        ), row=1, col=1)
        
        # Add enhanced target line
        fig.add_vline(x=80, line_dash="dash", line_color=self.color_palette['warning_light'], 
                      line_width=3, annotation_text="🎯 Target: 80%", 
                      annotation_position="top right", row=1, col=1)
        fig.add_vline(x=otif_mean*100, line_dash="solid", line_color=self.color_palette['primary'], 
                      line_width=3, annotation_text=f"📊 Mean: {otif_mean*100:.1f}%", 
                      annotation_position="top left", row=1, col=1)
        
        # Enhanced delay distribution with gradient
        fig.add_trace(go.Histogram(
            x=delay_samples,
            nbinsx=30,
            name='Delay Distribution',
            marker=dict(
                color=delay_samples,
                colorscale=[[0, self.color_palette['success']], 
                           [0.5, self.color_palette['accent4']], 
                           [1, self.color_palette['warning']]],
                line=dict(color='white', width=1)
            ),
            opacity=0.8,
            hovertemplate='Delay Range: %{x:.1f} days<br>Frequency: %{y}<extra></extra>'
        ), row=1, col=2)
        
        # Add enhanced reference lines
        fig.add_vline(x=delay_mean, line_dash="solid", line_color=self.color_palette['info'],
                      line_width=3, annotation_text=f"📊 Mean: {delay_mean:.1f}d", 
                      annotation_position="top right", row=1, col=2)
        fig.add_vline(x=delay_p95, line_dash="dash", line_color=self.color_palette['warning'],
                      line_width=3, annotation_text=f"📈 P95: {delay_p95:.1f}d", 
                      annotation_position="top left", row=1, col=2)
        
        fig.update_layout(
            height=500,
            title={
                'text': '🎲 Monte Carlo Risk Assessment: Statistical Distribution Analysis',
                'x': 0.5,
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            showlegend=False,
            template="plotly_white",
            font=dict(size=12)
        )
        
        fig.update_xaxes(title_text="OTIF Score (%)", row=1, col=1, gridcolor='rgba(128,128,128,0.2)')
        fig.update_xaxes(title_text="Delay (Days)", row=1, col=2, gridcolor='rgba(128,128,128,0.2)')
        fig.update_yaxes(title_text="Frequency", row=1, col=1, gridcolor='rgba(128,128,128,0.2)')
        fig.update_yaxes(title_text="Frequency", row=1, col=2, gridcolor='rgba(128,128,128,0.2)')
        
        return fig
    
    def create_capacity_utilization_chart(self, results: Dict[str, Any]) -> go.Figure:
        """Create stunning capacity utilization with gradient bars"""
        
        plan = results.get('optimized_plan', [])
        if not plan:
            return self._create_empty_chart("No capacity data available")
        
        plan_df = pd.DataFrame(plan)
        
        # Enhanced utilization percentages
        plan_df['weight_util_pct'] = plan_df['utilization_weight'] * 100
        plan_df['volume_util_pct'] = plan_df['utilization_volume'] * 100
        plan_df['avg_util_pct'] = (plan_df['weight_util_pct'] + plan_df['volume_util_pct']) / 2
        
        fig = go.Figure()
        
        # Enhanced weight utilization bars with gradient
        fig.add_trace(go.Bar(
            name='⚖️ Weight Utilization',
            x=plan_df['container_id'],
            y=plan_df['weight_util_pct'],
            marker=dict(
                color=plan_df['weight_util_pct'],
                colorscale=[[0, self.color_palette['info_light']], 
                           [0.5, self.color_palette['info']], 
                           [1, self.color_palette['primary']]],
                line=dict(color='white', width=1)
            ),
            opacity=0.8,
            hovertemplate='<b>%{x}</b><br>Weight Utilization: %{y:.1f}%<br>Weight: %{customdata:.0f} kg<extra></extra>',
            customdata=plan_df['total_weight_kg']
        ))
        
        # Enhanced volume utilization bars with gradient
        fig.add_trace(go.Bar(
            name='📦 Volume Utilization',
            x=plan_df['container_id'],
            y=plan_df['volume_util_pct'],
            marker=dict(
                color=plan_df['volume_util_pct'],
                colorscale=[[0, self.color_palette['accent4']], 
                           [0.5, self.color_palette['accent1']], 
                           [1, self.color_palette['warning']]],
                line=dict(color='white', width=1)
            ),
            opacity=0.8,
            hovertemplate='<b>%{x}</b><br>Volume Utilization: %{y:.1f}%<br>Volume: %{customdata:.1f} m³<extra></extra>',
            customdata=plan_df['total_volume_m3']
        ))
        
        # Add enhanced target line
        fig.add_hline(y=85, line_dash="dash", line_color=self.color_palette['success'], 
                      line_width=3, annotation_text="🎯 Target: 85%",
                      annotation_position="top right")
        
        # Add average utilization line
        avg_util = plan_df['avg_util_pct'].mean()
        fig.add_hline(y=avg_util, line_dash="dot", line_color=self.color_palette['accent3'], 
                      line_width=2, annotation_text=f"📊 Average: {avg_util:.1f}%",
                      annotation_position="bottom right")
        
        fig.update_layout(
            title={
                'text': '📦 Container Utilization Analysis: Weight vs Volume Efficiency',
                'x': 0.5,
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            xaxis_title='Container ID',
            yaxis_title='Utilization (%)',
            barmode='group',
            height=500,
            hovermode='x unified',
            template="plotly_white",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            ),
            font=dict(size=12),
            yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
            xaxis=dict(gridcolor='rgba(128,128,128,0.2)')
        )
        
        return fig
    
    def create_cost_breakdown_chart(self, results: Dict[str, Any]) -> go.Figure:
        """Create beautiful cost breakdown with modern styling"""
        
        plan = results.get('optimized_plan', [])
        if not plan:
            return self._create_empty_chart("No cost data available")
        
        plan_df = pd.DataFrame(plan)
        
        # Enhanced cost analysis
        cost_by_mode = plan_df.groupby('transport_mode').agg({
            'route_cost_eur': 'sum',
            'container_id': 'count',
            'total_weight_kg': 'sum'
        }).reset_index()
        
        cost_by_mode.columns = ['transport_mode', 'total_cost', 'container_count', 'total_weight']
        cost_by_mode['cost_per_kg'] = cost_by_mode['total_cost'] / cost_by_mode['total_weight']
        cost_by_mode['avg_cost_per_container'] = cost_by_mode['total_cost'] / cost_by_mode['container_count']
        
        # Create enhanced subplots
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('💰 Cost Distribution by Transport Mode', '📊 Cost Efficiency Analysis (€/kg)'),
            specs=[[{"type": "pie"}, {"type": "bar"}]]
        )
        
        # Enhanced donut chart with gradient colors
        colors = [self.color_palette['primary'], self.color_palette['info'], 
                 self.color_palette['success'], self.color_palette['warning'], 
                 self.color_palette['accent1'], self.color_palette['accent3']]
        
        fig.add_trace(go.Pie(
            labels=cost_by_mode['transport_mode'],
            values=cost_by_mode['total_cost'],
            name="Cost Distribution",
            hole=0.4,
            marker=dict(colors=colors[:len(cost_by_mode)], line=dict(color='white', width=2)),
            textinfo='label+percent',
            textfont_size=12,
            hovertemplate='<b>%{label}</b><br>Cost: €%{value:,.0f}<br>Share: %{percent}<br>Containers: %{customdata}<extra></extra>',
            customdata=cost_by_mode['container_count']
        ), row=1, col=1)
        
        # Enhanced cost efficiency bar chart with gradient
        fig.add_trace(go.Bar(
            x=cost_by_mode['transport_mode'],
            y=cost_by_mode['cost_per_kg'],
            name="Cost per kg",
            marker=dict(
                color=cost_by_mode['cost_per_kg'],
                colorscale=[[0, self.color_palette['success']], 
                           [0.5, self.color_palette['accent4']], 
                           [1, self.color_palette['warning']]],
                line=dict(color='white', width=1)
            ),
            opacity=0.8,
            hovertemplate='<b>%{x}</b><br>Cost/kg: €%{y:.2f}<br>Total Cost: €%{customdata:,.0f}<br>Containers: %{customdata2}<extra></extra>',
            customdata=cost_by_mode['total_cost'],
            customdata2=cost_by_mode['container_count']
        ), row=1, col=2)
        
        fig.update_layout(
            height=500,
            title={
                'text': '💰 Cost Analysis: Distribution and Efficiency Metrics',
                'x': 0.5,
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            showlegend=False,
            template="plotly_white",
            font=dict(size=12)
        )
        
        fig.update_yaxes(title_text="Cost per kg (EUR)", row=1, col=2, gridcolor='rgba(128,128,128,0.2)')
        
        return fig
    
    def create_timeline_chart(self, results: Dict[str, Any]) -> go.Figure:
        """Create beautiful shipment timeline with modern Gantt-style chart"""
        
        plan = results.get('optimized_plan', [])
        if not plan:
            return self._create_empty_chart("No timeline data available")
        
        plan_df = pd.DataFrame(plan)
        
        # Generate enhanced timeline data
        base_date = datetime.now()
        timeline_data = []
        
        # Transport mode colors
        mode_colors = {
            'Air_Express': self.color_palette['warning'],
            'Air_Standard': self.color_palette['info'], 
            'Ground_Express': self.color_palette['success'],
            'Ground_Standard': self.color_palette['primary'],
            'Ocean_Standard': self.color_palette['accent3']
        }
        
        for idx, row in plan_df.iterrows():
            departure = base_date + timedelta(days=idx * 0.3)  # Stagger departures
            
            # Enhanced transit time calculation
            transit_days = {
                'Air_Express': 3,
                'Air_Standard': 7, 
                'Ground_Express': 2,
                'Ground_Standard': 5,
                'Ocean_Standard': 21
            }.get(row['transport_mode'], 7)
            
            arrival = departure + timedelta(days=transit_days)
            
            timeline_data.append({
                'container_id': row['container_id'],
                'departure': departure,
                'arrival': arrival,
                'transport_mode': row['transport_mode'],
                'cost': row['route_cost_eur'],
                'utilization': (row['utilization_weight'] + row['utilization_volume']) / 2,
                'duration': transit_days,
                'color': mode_colors.get(row['transport_mode'], self.color_palette['primary'])
            })
        
        timeline_df = pd.DataFrame(timeline_data)
        
        # Create enhanced Gantt chart
        fig = px.timeline(
            timeline_df,
            x_start="departure",
            x_end="arrival", 
            y="container_id",
            color="transport_mode",
            color_discrete_map=mode_colors,
            title="📅 Shipment Timeline: Departure and Arrival Schedule",
            hover_data=['cost', 'utilization', 'duration']
        )
        
        # Enhanced styling
        fig.update_traces(
            marker_line_width=2,
            marker_line_color="white",
            opacity=0.8,
            hovertemplate='<b>%{y}</b><br>' +
                         'Mode: %{color}<br>' +
                         'Departure: %{x_start}<br>' +
                         'Arrival: %{x_end}<br>' +
                         'Duration: %{customdata[2]} days<br>' +
                         'Cost: €%{customdata[0]:,.2f}<br>' +
                         'Utilization: %{customdata[1]:.1%}<extra></extra>'
        )
        
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_layout(
            height=600, 
            xaxis_title="Timeline",
            yaxis_title="Container ID",
            template="plotly_white",
            title_font_size=20,
            title_font_color='#2c3e50',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.3,
                xanchor="center",
                x=0.5
            ),
            font=dict(size=12)
        )
        
        return fig
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """Create beautiful empty state chart"""
        fig = go.Figure()
        
        fig.add_annotation(
            text=f"📊 {message}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            font=dict(size=20, color=self.color_palette['info']),
            showarrow=False
        )
        
        fig.update_layout(
            height=400,
            template="plotly_white",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        
        return fig

def create_dashboard_page(results: Dict[str, Any], historical_data: pd.DataFrame = None):
    """Create comprehensive dashboard page with stunning visuals"""
    
    dashboard = SupplyChainDashboard()
    
    # Beautiful header with gradient
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
               padding: 3rem 2rem; border-radius: 20px; margin-bottom: 2rem; 
               box-shadow: 0 10px 30px rgba(102,126,234,0.3);">
        <h1 style="color: white; text-align: center; font-size: 2.5rem; margin-bottom: 1rem; font-family: 'Inter', sans-serif;">
            📊 Advanced Analytics Dashboard
        </h1>
        <p style="color: white; text-align: center; font-size: 1.2rem; opacity: 0.9; margin: 0;">
            Comprehensive supply chain performance analysis with real-time insights and predictive analytics
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Executive Summary
    st.markdown("### 🎯 Executive Performance Overview")
    exec_fig = dashboard.create_executive_summary(results)
    st.plotly_chart(exec_fig, use_container_width=True)
    
    # Enhanced tabs with beautiful styling
    tab1, tab2, tab3, tab4 = st.tabs([
        "🚛 Route Analytics", 
        "⚠️ Risk Assessment", 
        "📦 Capacity Planning", 
        "💰 Financial Analysis"
    ])
    
    with tab1:
        st.markdown("#### 🚚 Transportation Performance Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            route_fig = dashboard.create_route_analysis_chart(results)
            st.plotly_chart(route_fig, use_container_width=True)
        
        with col2:
            timeline_fig = dashboard.create_timeline_chart(results)
            st.plotly_chart(timeline_fig, use_container_width=True)
    
    with tab2:
        st.markdown("#### 🎲 Monte Carlo Risk Analysis")
        risk_fig = dashboard.create_risk_distribution_chart(results['risk_analysis'])
        st.plotly_chart(risk_fig, use_container_width=True)
        
        # Risk summary metrics
        risk = results['risk_analysis']
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "📊 Average OTIF",
                f"{risk.get('otif_statistics', {}).get('mean', 0)*100:.1f}%",
                delta=f"{(risk.get('otif_statistics', {}).get('mean', 0)*100) - 80:.1f}% vs target"
            )
        
        with col2:
            st.metric(
                "⏱️ Mean Delay",
                f"{risk.get('delay_statistics', {}).get('mean_delay_days', 0):.1f} days",
                delta=f"-{2.5 - risk.get('delay_statistics', {}).get('mean_delay_days', 0):.1f} days vs baseline"
            )
        
        with col3:
            st.metric(
                "📈 P95 Delay",
                f"{risk.get('delay_statistics', {}).get('p95_delay_days', 0):.1f} days",
                delta=f"Risk percentile"
            )
        
        with col4:
            st.metric(
                "⚠️ Risk Score",
                f"{risk.get('risk_score', 0):.1f}/100",
                delta=f"{'Low' if risk.get('risk_score', 0) < 30 else 'Medium' if risk.get('risk_score', 0) < 60 else 'High'} risk"
            )
    
    with tab3:
        st.markdown("#### 📦 Container Utilization & Capacity Planning")
        capacity_fig = dashboard.create_capacity_utilization_chart(results)
        st.plotly_chart(capacity_fig, use_container_width=True)
        
        # Capacity insights
        plan = results.get('optimized_plan', [])
        if plan:
            plan_df = pd.DataFrame(plan)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📊 Utilization Statistics**")
                avg_weight_util = plan_df['utilization_weight'].mean() * 100
                avg_volume_util = plan_df['utilization_volume'].mean() * 100
                
                st.info(f"""
                - **Average Weight Utilization:** {avg_weight_util:.1f}%
                - **Average Volume Utilization:** {avg_volume_util:.1f}%
                - **Total Containers:** {len(plan_df)}
                - **Best Performing Container:** {plan_df.loc[plan_df['utilization_weight'].idxmax(), 'container_id']}
                """)
            
            with col2:
                st.markdown("**🎯 Optimization Opportunities**")
                underutilized = plan_df[plan_df['utilization_weight'] < 0.7]
                
                if len(underutilized) > 0:
                    st.warning(f"""
                    - **{len(underutilized)} containers** below 70% utilization
                    - **Potential savings:** €{underutilized['route_cost_eur'].sum():,.0f}
                    - **Consolidation opportunity:** {len(underutilized) // 2} fewer containers possible
                    """)
                else:
                    st.success("🎉 All containers are well-utilized (>70%)")
    
    with tab4:
        st.markdown("#### 💰 Financial Performance & Cost Analysis")
        cost_fig = dashboard.create_cost_breakdown_chart(results)
        st.plotly_chart(cost_fig, use_container_width=True)
        
        # Financial summary
        kpis = results['kpis']
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
                       padding: 1.5rem; border-radius: 10px; color: white;">
                <h4 style="color: white; margin-bottom: 1rem;">💰 Cost Performance</h4>
                <p style="font-size: 2rem; font-weight: bold; margin: 0;">
                    €{:,.0f}
                </p>
                <p style="opacity: 0.9; margin: 0;">Total Optimization Cost</p>
            </div>
            """.format(kpis.get('total_cost_eur', 0)), unsafe_allow_html=True)
        
        with col2:
            cost_reduction = (1 - kpis.get('cost_ratio', 1)) * 100
            st.markdown("""
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                       padding: 1.5rem; border-radius: 10px; color: white;">
                <h4 style="color: white; margin-bottom: 1rem;">📈 Savings Achieved</h4>
                <p style="font-size: 2rem; font-weight: bold; margin: 0;">
                    {:.1f}%
                </p>
                <p style="opacity: 0.9; margin: 0;">Cost Reduction</p>
            </div>
            """.format(cost_reduction), unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                       padding: 1.5rem; border-radius: 10px; color: white;">
                <h4 style="color: white; margin-bottom: 1rem;">📦 Efficiency</h4>
                <p style="font-size: 2rem; font-weight: bold; margin: 0;">
                    {:.0f}%
                </p>
                <p style="opacity: 0.9; margin: 0;">Container Utilization</p>
            </div>
            """.format(kpis.get('avg_container_utilization', 0) * 100), unsafe_allow_html=True)
