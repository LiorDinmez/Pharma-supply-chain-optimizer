"""
Optimization Wrapper for Streamlit Integration - FIXED VERSION
============================================================
This module provides a simplified interface to the AdvancedOptimizationEngine
for use in the Streamlit application. Fixed circular import issue.
"""

import pandas as pd
import sqlite3
from pathlib import Path
from typing import Dict, Any, Tuple
import logging

class OptimizationService:
    """Service class that wraps the optimization engine for easy use in Streamlit"""
    
    def __init__(self, config_path: str = None):
        """Initialize the optimization service"""
        self.logger = logging.getLogger(__name__)
        self.engine = None
        self.config_path = config_path
        self._initialize_engine()
        
    def _initialize_engine(self):
        """Initialize the optimization engine with dynamic import"""
        try:
            # Dynamic import to avoid circular import
            from optimization_engine_v2 import AdvancedOptimizationEngine
            self.engine = AdvancedOptimizationEngine(self.config_path)
        except Exception as e:
            self.logger.error(f"Failed to initialize optimization engine: {e}")
            self.engine = None
    
    def load_sample_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load the sample batch and route data"""
        try:
            batches_df = pd.read_csv('sample_data/sample_batches.csv')
            routes_df = pd.read_csv('sample_data/sample_routes.csv')
            return batches_df, routes_df
        except FileNotFoundError as e:
            self.logger.error(f"Sample data files not found: {e}")
            raise
    
    def validate_data(self, batches_df: pd.DataFrame, routes_df: pd.DataFrame) -> Dict[str, Any]:
        """Validate input data and return validation results"""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'summary': {}
        }
        
        # Check batch data
        required_batch_cols = [
            'batch_id', 'material', 'quantity_doses', 'value_eur', 
            'weight_kg', 'volume_m3', 'expected_release_date',
            'current_station', 'target_market', 'days_in_queue', 'delay_reason'
        ]
        
        missing_batch_cols = set(required_batch_cols) - set(batches_df.columns)
        if missing_batch_cols:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Missing batch columns: {missing_batch_cols}")
        
        # Check route data
        required_route_cols = [
            'route_id', 'origin', 'destination_region', 'transport_mode',
            'capacity_kg', 'capacity_m3', 'cost_per_kg', 'transit_days'
        ]
        
        missing_route_cols = set(required_route_cols) - set(routes_df.columns)
        if missing_route_cols:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Missing route columns: {missing_route_cols}")
        
        # Data quality checks
        if validation_results['valid']:
            # Check for negative values
            numeric_batch_cols = ['quantity_doses', 'value_eur', 'weight_kg', 'volume_m3', 'days_in_queue']
            for col in numeric_batch_cols:
                if (batches_df[col] < 0).any():
                    validation_results['warnings'].append(f"Negative values found in {col}")
            
            numeric_route_cols = ['capacity_kg', 'capacity_m3', 'cost_per_kg', 'transit_days']
            for col in numeric_route_cols:
                if (routes_df[col] < 0).any():
                    validation_results['warnings'].append(f"Negative values found in {col}")
            
            # Summary statistics
            validation_results['summary'] = {
                'total_batches': len(batches_df),
                'total_routes': len(routes_df),
                'total_value_eur': batches_df['value_eur'].sum(),
                'total_weight_kg': batches_df['weight_kg'].sum(),
                'total_volume_m3': batches_df['volume_m3'].sum(),
                'avg_days_in_queue': batches_df['days_in_queue'].mean(),
                'critical_batches': len(batches_df[batches_df['delay_reason'] == 'Investigation']),
                'available_transport_modes': routes_df['transport_mode'].unique().tolist()
            }
        
        return validation_results
    
    def run_optimization(self, batches_df: pd.DataFrame, routes_df: pd.DataFrame, 
                        constraints: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the optimization and return results"""
        
        if self.engine is None:
            raise RuntimeError("Optimization engine not initialized. Please check optimization_engine_v2.py")
        
        # Default constraints
        default_constraints = {
            'max_transit_days': 21,
            'min_otif_rate': 0.8,
            'alpha': 0.01
        }
        
        if constraints:
            default_constraints.update(constraints)
        
        try:
            # Run the optimization
            results = self.engine.optimize_shipment_plan(
                batches_df=batches_df,
                routes_df=routes_df,
                constraints=default_constraints
            )
            
            # Add some additional metrics for the dashboard
            results['input_summary'] = {
                'total_batches': len(batches_df),
                'total_routes': len(routes_df),
                'total_input_value': batches_df['value_eur'].sum(),
                'total_input_weight': batches_df['weight_kg'].sum(),
                'avg_queue_time': batches_df['days_in_queue'].mean()
            }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Optimization failed: {e}")
            raise
    
    def get_optimization_history(self) -> pd.DataFrame:
        """Retrieve optimization history from the database"""
        if self.engine is None:
            return pd.DataFrame()
            
        db_path = Path(self.engine.cfg["db_path"])
        
        if not db_path.exists():
            return pd.DataFrame()
        
        try:
            conn = sqlite3.connect(db_path)
            history_df = pd.read_sql_query(
                "SELECT * FROM history ORDER BY ts DESC LIMIT 50", 
                conn
            )
            conn.close()
            
            # Convert timestamp to datetime
            if not history_df.empty:
                history_df['timestamp'] = pd.to_datetime(history_df['ts'])
                history_df['run_number'] = range(len(history_df), 0, -1)
            
            return history_df
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve history: {e}")
            return pd.DataFrame()
    
    def clear_optimization_history(self) -> bool:
        """Clear the optimization history database"""
        if self.engine is None:
            return False
            
        db_path = Path(self.engine.cfg["db_path"])
        
        if not db_path.exists():
            return True
        
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("DELETE FROM history")
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear history: {e}")
            return False
    
    def export_results(self, results: Dict[str, Any], format: str = 'csv') -> str:
        """Export optimization results to various formats"""
        
        if format.lower() == 'csv':
            # Convert shipment plan to DataFrame
            plan_df = pd.DataFrame(results['optimized_plan'])
            csv_content = plan_df.to_csv(index=False)
            return csv_content
        
        elif format.lower() == 'summary':
            # Generate a text summary
            kpis = results['kpis']
            risk = results['risk_analysis']
            otif = results['otif_compliance']
            
            summary = f"""
OPTIMIZATION RESULTS SUMMARY
============================

COST OPTIMIZATION:
- Total Cost: €{kpis.get('total_cost_eur', 0):,.2f}
- Cost Reduction: {(1 - kpis.get('cost_ratio', 1)) * 100:.1f}%
- Average Container Utilization: {kpis.get('avg_container_utilization', 0) * 100:.1f}%

OPERATIONAL EFFICIENCY:
- Total Containers: {kpis.get('total_containers', 0)}
- Cycle Time Improvement: {kpis.get('cycle_time_improvement', 0) * 100:.1f}%
- Total Weight: {kpis.get('total_weight_kg', 0):,.1f} kg
- Total Volume: {kpis.get('total_volume_m3', 0):,.1f} m³

RISK ASSESSMENT:
- OTIF Score: {risk.get('otif_statistics', {}).get('mean', 0) * 100:.1f}%
- Risk Score: {risk.get('risk_score', 0):.1f}/100
- Mean Delay: {risk.get('delay_statistics', {}).get('mean_delay_days', 0):.1f} days
- P95 Delay: {risk.get('delay_statistics', {}).get('p95_delay_days', 0):.1f} days

COMPLIANCE:
- OTIF Rate: {otif.get('otif_rate', 0) * 100:.1f}%
- On-time Containers: {otif.get('on_time_containers', 0)}/{otif.get('total_containers', 0)}
- Meets Target: {'✅ Yes' if otif.get('meets_target', False) else '❌ No'}
"""
            return summary
        
        else:
            raise ValueError(f"Unsupported export format: {format}")

# Create a function that returns the service instance (lazy initialization)
_optimization_service = None

def get_optimization_service() -> OptimizationService:
    """Get the global optimization service instance"""
    global _optimization_service
    if _optimization_service is None:
        _optimization_service = OptimizationService()
    return _optimization_service
