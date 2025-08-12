import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Tuple
import logging

class PharmaDatabaseManager:
    def __init__(self, db_path: str = "pharma_supply_chain.db"):
        self.db_path = db_path
        self.setup_logging()
        self.init_database()
    
    def setup_logging(self):
        """Setup logging for database operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('pharma_dashboard.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def init_database(self):
        """Initialize database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Shipment Plans Table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS shipment_plans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plan_date DATE NOT NULL,
                        batch_id TEXT NOT NULL,
                        route_id TEXT NOT NULL,
                        transport_mode TEXT NOT NULL,
                        planned_weight_kg REAL NOT NULL,
                        planned_value_eur REAL NOT NULL,
                        planned_delivery_date DATE NOT NULL,
                        priority TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        plan_version INTEGER DEFAULT 1
                    )
                ''')
                
                # Actual Results Table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS actual_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plan_id INTEGER,
                        batch_id TEXT NOT NULL,
                        actual_delivery_date DATE,
                        actual_weight_kg REAL,
                        actual_value_eur REAL,
                        delivery_status TEXT,
                        otif_status TEXT,
                        delay_days INTEGER,
                        cost_variance_eur REAL,
                        notes TEXT,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (plan_id) REFERENCES shipment_plans (id)
                    )
                ''')
                
                # KPI History Table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS kpi_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE NOT NULL,
                        metric_name TEXT NOT NULL,
                        planned_value REAL,
                        actual_value REAL,
                        variance REAL,
                        variance_percentage REAL,
                        target_value REAL,
                        status TEXT,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # OTIF Performance Table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS otif_performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        month_year TEXT NOT NULL,
                        customer_name TEXT NOT NULL,
                        total_orders INTEGER NOT NULL,
                        on_time_orders INTEGER NOT NULL,
                        in_full_orders INTEGER NOT NULL,
                        otif_orders INTEGER NOT NULL,
                        otif_percentage REAL NOT NULL,
                        target_otif REAL DEFAULT 80.0,
                        performance_status TEXT,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Cost Optimization History
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cost_optimization (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        optimization_date DATE NOT NULL,
                        total_cost_eur REAL NOT NULL,
                        container_utilization_percent REAL NOT NULL,
                        route_optimization_savings REAL,
                        container_loading_efficiency REAL,
                        cost_per_kg REAL,
                        notes TEXT,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    def log_shipment_plan(self, plan_data: Dict) -> int:
        """Log a shipment plan and return the plan ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO shipment_plans (
                        plan_date, batch_id, route_id, transport_mode, 
                        planned_weight_kg, planned_value_eur, planned_delivery_date, priority
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    plan_data['plan_date'],
                    plan_data['batch_id'],
                    plan_data['route_id'],
                    plan_data['transport_mode'],
                    plan_data['planned_weight_kg'],
                    plan_data['planned_value_eur'],
                    plan_data['planned_delivery_date'],
                    plan_data['priority']
                ))
                
                plan_id = cursor.lastrowid
                conn.commit()
                self.logger.info(f"Shipment plan logged with ID: {plan_id}")
                return plan_id
                
        except Exception as e:
            self.logger.error(f"Error logging shipment plan: {e}")
            raise
    
    def log_actual_result(self, actual_data: Dict) -> int:
        """Log actual delivery results"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO actual_results (
                        plan_id, batch_id, actual_delivery_date, actual_weight_kg,
                        actual_value_eur, delivery_status, otif_status, delay_days,
                        cost_variance_eur, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    actual_data.get('plan_id'),
                    actual_data['batch_id'],
                    actual_data['actual_delivery_date'],
                    actual_data.get('actual_weight_kg'),
                    actual_data.get('actual_value_eur'),
                    actual_data['delivery_status'],
                    actual_data['otif_status'],
                    actual_data.get('delay_days', 0),
                    actual_data.get('cost_variance_eur', 0),
                    actual_data.get('notes', '')
                ))
                
                result_id = cursor.lastrowid
                conn.commit()
                self.logger.info(f"Actual result logged with ID: {result_id}")
                return result_id
                
        except Exception as e:
            self.logger.error(f"Error logging actual result: {e}")
            raise
    
    def log_kpi_metric(self, kpi_data: Dict):
        """Log KPI metrics for plan vs actual comparison"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO kpi_history (
                        date, metric_name, planned_value, actual_value, 
                        variance, variance_percentage, target_value, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    kpi_data['date'],
                    kpi_data['metric_name'],
                    kpi_data.get('planned_value'),
                    kpi_data.get('actual_value'),
                    kpi_data.get('variance'),
                    kpi_data.get('variance_percentage'),
                    kpi_data.get('target_value'),
                    kpi_data.get('status', 'Unknown')
                ))
                
                conn.commit()
                self.logger.info(f"KPI metric logged: {kpi_data['metric_name']}")
                
        except Exception as e:
            self.logger.error(f"Error logging KPI metric: {e}")
            raise
    
    def log_otif_performance(self, otif_data: Dict):
        """Log OTIF performance data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate performance status
                target_otif = otif_data.get('target_otif', 80.0)
                performance_status = 'Target Met' if otif_data['otif_percentage'] >= target_otif else 'Below Target'
                
                cursor.execute('''
                    INSERT INTO otif_performance (
                        month_year, customer_name, total_orders, on_time_orders,
                        in_full_orders, otif_orders, otif_percentage, target_otif, performance_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    otif_data['month_year'],
                    otif_data['customer_name'],
                    otif_data['total_orders'],
                    otif_data['on_time_orders'],
                    otif_data['in_full_orders'],
                    otif_data['otif_orders'],
                    otif_data['otif_percentage'],
                    target_otif,
                    performance_status
                ))
                
                conn.commit()
                self.logger.info(f"OTIF performance logged for {otif_data['customer_name']}")
                
        except Exception as e:
            self.logger.error(f"Error logging OTIF performance: {e}")
            raise
    
    def log_cost_optimization(self, cost_data: Dict):
        """Log cost optimization results"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO cost_optimization (
                        optimization_date, total_cost_eur, container_utilization_percent,
                        route_optimization_savings, container_loading_efficiency,
                        cost_per_kg, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    cost_data['optimization_date'],
                    cost_data['total_cost_eur'],
                    cost_data['container_utilization_percent'],
                    cost_data.get('route_optimization_savings', 0),
                    cost_data.get('container_loading_efficiency', 0),
                    cost_data.get('cost_per_kg', 0),
                    cost_data.get('notes', '')
                ))
                
                conn.commit()
                self.logger.info(f"Cost optimization logged for {cost_data['optimization_date']}")
                
        except Exception as e:
            self.logger.error(f"Error logging cost optimization: {e}")
            raise
    
    def get_plan_vs_actual_kpis(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Get plan vs actual KPI comparison"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = '''
                    SELECT 
                        sp.plan_date,
                        sp.batch_id,
                        sp.planned_delivery_date,
                        ar.actual_delivery_date,
                        sp.planned_weight_kg,
                        ar.actual_weight_kg,
                        sp.planned_value_eur,
                        ar.actual_value_eur,
                        ar.delay_days,
                        ar.cost_variance_eur,
                        ar.otif_status,
                        CASE 
                            WHEN ar.actual_delivery_date <= sp.planned_delivery_date THEN 'On Time'
                            ELSE 'Delayed'
                        END as delivery_performance
                    FROM shipment_plans sp
                    LEFT JOIN actual_results ar ON sp.id = ar.plan_id
                    WHERE sp.plan_date BETWEEN ? AND ?
                    ORDER BY sp.plan_date DESC
                '''
                
                df = pd.read_sql_query(query, conn, params=[start_date, end_date])
                return df
                
        except Exception as e:
            self.logger.error(f"Error getting plan vs actual KPIs: {e}")
            return pd.DataFrame()
    
    def get_otif_trends(self, months: int = 6) -> pd.DataFrame:
        """Get OTIF performance trends over time"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = '''
                    SELECT 
                        month_year,
                        customer_name,
                        total_orders,
                        otif_orders,
                        otif_percentage,
                        target_otif,
                        performance_status
                    FROM otif_performance
                    ORDER BY month_year DESC
                    LIMIT ?
                '''
                
                df = pd.read_sql_query(query, conn, params=[months * 5])  # 5 customers per month
                return df
                
        except Exception as e:
            self.logger.error(f"Error getting OTIF trends: {e}")
            return pd.DataFrame()
    
    def get_cost_optimization_history(self, days: int = 30) -> pd.DataFrame:
        """Get cost optimization history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = '''
                    SELECT 
                        optimization_date,
                        total_cost_eur,
                        container_utilization_percent,
                        route_optimization_savings,
                        cost_per_kg
                    FROM cost_optimization
                    WHERE optimization_date >= date('now', '-{} days')
                    ORDER BY optimization_date DESC
                '''.format(days)
                
                df = pd.read_sql_query(query, conn)
                return df
                
        except Exception as e:
            self.logger.error(f"Error getting cost optimization history: {e}")
            return pd.DataFrame()
    
    def calculate_plan_vs_actual_metrics(self, start_date: str, end_date: str) -> Dict:
        """Calculate comprehensive plan vs actual metrics"""
        try:
            df = self.get_plan_vs_actual_kpis(start_date, end_date)
            
            if df.empty:
                return {}
            
            metrics = {
                'total_planned_shipments': len(df),
                'total_actual_shipments': len(df[df['actual_delivery_date'].notna()]),
                'on_time_deliveries': len(df[df['delivery_performance'] == 'On Time']),
                'delayed_deliveries': len(df[df['delivery_performance'] == 'Delayed']),
                'on_time_percentage': 0,
                'average_delay_days': 0,
                'cost_variance_total': 0,
                'weight_accuracy': 0,
                'value_accuracy': 0
            }
            
            if metrics['total_actual_shipments'] > 0:
                metrics['on_time_percentage'] = (metrics['on_time_deliveries'] / metrics['total_actual_shipments']) * 100
                metrics['average_delay_days'] = df['delay_days'].mean()
                metrics['cost_variance_total'] = df['cost_variance_eur'].sum()
                
                # Calculate accuracy metrics
                weight_diff = abs(df['planned_weight_kg'] - df['actual_weight_kg']).sum()
                weight_total = df['planned_weight_kg'].sum()
                if weight_total > 0:
                    metrics['weight_accuracy'] = ((weight_total - weight_diff) / weight_total) * 100
                
                value_diff = abs(df['planned_value_eur'] - df['actual_value_eur']).sum()
                value_total = df['planned_value_eur'].sum()
                if value_total > 0:
                    metrics['value_accuracy'] = ((value_total - value_diff) / value_total) * 100
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating plan vs actual metrics: {e}")
            return {}
    
    def export_data_to_excel(self, filepath: str):
        """Export all database data to Excel for analysis"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get all table names
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                # Export each table to Excel
                with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                    for table in tables:
                        table_name = table[0]
                        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                        df.to_excel(writer, sheet_name=table_name, index=False)
                
                self.logger.info(f"Data exported to Excel: {filepath}")
                
        except Exception as e:
            self.logger.error(f"Error exporting data to Excel: {e}")
            raise

# Example usage and testing
if __name__ == "__main__":
    # Initialize database
    db_manager = PharmaDatabaseManager()
    
    # Test logging a shipment plan
    test_plan = {
        'plan_date': '2025-01-15',
        'batch_id': 'BATCH_0001',
        'route_id': 'R001',
        'transport_mode': 'Road',
        'planned_weight_kg': 2500.0,
        'planned_value_eur': 75000.0,
        'planned_delivery_date': '2025-01-18',
        'priority': 'High'
    }
    
    plan_id = db_manager.log_shipment_plan(test_plan)
    print(f"Test plan logged with ID: {plan_id}")
    
    # Test logging actual result
    test_result = {
        'plan_id': plan_id,
        'batch_id': 'BATCH_0001',
        'actual_delivery_date': '2025-01-19',
        'actual_weight_kg': 2480.0,
        'actual_value_eur': 74500.0,
        'delivery_status': 'Delivered',
        'otif_status': 'Partial',
        'delay_days': 1,
        'cost_variance_eur': -500.0,
        'notes': 'Minor weight variance due to packaging'
    }
    
    result_id = db_manager.log_actual_result(test_result)
    print(f"Test result logged with ID: {result_id}")
    
    print("Database setup and testing completed successfully!")

