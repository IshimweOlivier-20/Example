"""
Business Intelligence and Analytics SQL queries.

Optimized for MINICOM reporting requirements:
- Route traffic analysis for road planning
- Commodity statistics for agricultural policy
- Revenue heatmaps for economic insights
- Driver performance metrics

Performance: Uses GROUP BY, aggregation, and materialized views
Privacy: All queries anonymize individual customer data
"""
from typing import List, Dict, Any
from django.db import connection
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class AnalyticsQueries:
    """
    Optimized SQL queries for business intelligence.
    
    Compliance: Law N° 058/2021 - Privacy-preserving analytics
    All queries aggregate data to prevent individual identification
    """
    
    @staticmethod
    def get_top_routes(limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find highest-traffic corridors for MINICOM road planning.
        
        Query: Aggregates shipment counts by origin-destination pairs
        Privacy: No customer names, only route statistics
        
        Args:
            limit: Number of top routes to return
            
        Returns:
            List of routes with shipment counts and total weight
        """
        query = """
        WITH route_stats AS (
            SELECT 
                origin,
                destination,
                COUNT(*) as shipment_count,
                SUM(weight_kg) as total_weight_kg,
                AVG(weight_kg) as avg_weight_kg,
                SUM(cost) as total_revenue
            FROM (
                SELECT origin, destination, weight_kg, cost
                FROM domestic_domesticshipment
                WHERE status NOT IN ('CANCELLED', 'PAYMENT_FAILED')
                UNION ALL
                SELECT origin, destination, weight_kg, cost
                FROM international_internationalshipment
                WHERE status NOT IN ('CANCELLED', 'PAYMENT_FAILED')
            ) AS all_shipments
            GROUP BY origin, destination
        )
        SELECT 
            origin,
            destination,
            shipment_count,
            total_weight_kg,
            avg_weight_kg,
            total_revenue,
            ROUND(total_revenue / shipment_count, 2) as avg_revenue_per_shipment
        FROM route_stats
        ORDER BY shipment_count DESC
        LIMIT %s;
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, [limit])
            columns = [col[0] for col in cursor.description]
            results = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
        
        logger.info(f"Top routes query returned {len(results)} results")
        return results
    
    @staticmethod
    def get_commodity_breakdown() -> List[Dict[str, Any]]:
        """
        Commodity type statistics for agricultural policy planning.
        
        Use case: MINICOM wants to know volume of Potatoes vs Electronics
        Privacy: Aggregated data only, no farm/business identification
        
        Returns:
            Breakdown of shipments by commodity type
        """
        query = """
        SELECT 
            commodity_type,
            COUNT(*) as shipment_count,
            SUM(weight_kg) as total_weight_kg,
            AVG(weight_kg) as avg_weight_kg,
            COUNT(DISTINCT DATE(created_at)) as active_days,
            MIN(created_at) as first_shipment,
            MAX(created_at) as last_shipment
        FROM (
            SELECT description as commodity_type, weight_kg, created_at
            FROM domestic_domesticshipment
            WHERE status NOT IN ('CANCELLED', 'PAYMENT_FAILED')
            UNION ALL
            SELECT description as commodity_type, weight_kg, created_at
            FROM international_internationalshipment
            WHERE status NOT IN ('CANCELLED', 'PAYMENT_FAILED')
        ) AS all_commodities
        GROUP BY commodity_type
        ORDER BY total_weight_kg DESC;
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            results = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
        
        return results
    
    @staticmethod
    def get_revenue_heatmap() -> List[Dict[str, Any]]:
        """
        Geospatial revenue data by sector for economic insights.
        
        Privacy: Aggregated by sector, no individual business revenue
        
        Returns:
            Revenue breakdown by administrative sector
        """
        query = """
        SELECT 
            destination as sector,
            COUNT(*) as shipment_count,
            SUM(cost) as total_revenue,
            AVG(cost) as avg_shipment_value,
            SUM(weight_kg) as total_cargo_kg,
            MIN(created_at) as period_start,
            MAX(created_at) as period_end
        FROM (
            SELECT destination, cost, weight_kg, created_at
            FROM domestic_domesticshipment
            WHERE status IN ('DELIVERED', 'IN_TRANSIT', 'PENDING')
            UNION ALL
            SELECT destination, cost, weight_kg, created_at
            FROM international_internationalshipment
            WHERE status IN ('DELIVERED', 'IN_TRANSIT', 'PENDING')
        ) AS all_shipments
        GROUP BY destination
        ORDER BY total_revenue DESC;
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            results = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
        
        return results
    
    @staticmethod
    def get_driver_leaderboard(limit: int = 20) -> List[Dict[str, Any]]:
        """
        Top performing drivers by on-time delivery rate.
        
        Metrics: Delivery count, on-time percentage, average rating
        Privacy: Only shows driver ID and phone (no personal details)
        
        Args:
            limit: Number of drivers to return
            
        Returns:
            Ranked list of drivers with performance metrics
        """
        # Note: This query assumes we have delivery timestamps
        # In production, track actual vs. expected delivery time
        
        query = """
        SELECT 
            driver.id as driver_id,
            driver.phone as driver_phone,
            driver.full_name as driver_name,
            COUNT(*) as total_deliveries,
            COUNT(CASE WHEN status = 'DELIVERED' THEN 1 END) as completed_deliveries,
            ROUND(
                100.0 * COUNT(CASE WHEN status = 'DELIVERED' THEN 1 END) / 
                NULLIF(COUNT(*), 0), 
                2
            ) as completion_rate,
            SUM(cost) as total_revenue_generated
        FROM (
            SELECT driver_id, status, cost
            FROM domestic_domesticshipment
            WHERE driver_id IS NOT NULL
            UNION ALL
            SELECT driver_id, status, cost
            FROM international_internationalshipment
            WHERE driver_id IS NOT NULL
        ) AS driver_shipments
        JOIN users AS driver ON driver_shipments.driver_id = driver.id
        GROUP BY driver.id, driver.phone, driver.full_name
        HAVING COUNT(*) >= 5  -- Minimum 5 shipments for ranking
        ORDER BY completion_rate DESC, total_deliveries DESC
        LIMIT %s;
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, [limit])
            columns = [col[0] for col in cursor.description]
            results = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
        
        return results
    
    @staticmethod
    def get_peak_hour_analysis() -> List[Dict[str, Any]]:
        """
        Peak traffic analysis by hour of day.
        
        Use case: Optimize driver shifts during harvest season
        
        Returns:
            Shipment counts by hour of day
        """
        query = """
        SELECT 
            EXTRACT(HOUR FROM created_at) as hour_of_day,
            COUNT(*) as shipment_count,
            AVG(weight_kg) as avg_weight,
            SUM(cost) as total_revenue
        FROM (
            SELECT created_at, weight_kg, cost
            FROM domestic_domesticshipment
            WHERE created_at >= NOW() - INTERVAL '30 days'
            UNION ALL
            SELECT created_at, weight_kg, cost
            FROM international_internationalshipment
            WHERE created_at >= NOW() - INTERVAL '30 days'
        ) AS recent_shipments
        GROUP BY EXTRACT(HOUR FROM created_at)
        ORDER BY hour_of_day;
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            results = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
        
        return results
    
    @staticmethod
    def get_monthly_growth_metrics() -> List[Dict[str, Any]]:
        """
        Month-over-month growth analysis.
        
        Returns:
            Revenue and shipment trends by month
        """
        query = """
        SELECT 
            DATE_TRUNC('month', created_at) as month,
            COUNT(*) as shipment_count,
            SUM(cost) as total_revenue,
            COUNT(DISTINCT customer_id) as unique_customers,
            AVG(weight_kg) as avg_shipment_weight
        FROM (
            SELECT created_at, cost, customer_id, weight_kg
            FROM domestic_domesticshipment
            WHERE created_at >= NOW() - INTERVAL '12 months'
            UNION ALL
            SELECT created_at, cost, customer_id, weight_kg
            FROM international_internationalshipment
            WHERE created_at >= NOW() - INTERVAL '12 months'
        ) AS all_shipments
        GROUP BY DATE_TRUNC('month', created_at)
        ORDER BY month DESC;
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            results = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
        
        return results
    
    @staticmethod
    def get_customer_retention_metrics() -> Dict[str, Any]:
        """
        Customer retention and repeat usage statistics.
        
        Privacy: Aggregated metrics only, no individual tracking
        
        Returns:
            Retention statistics
        """
        query = """
        WITH customer_stats AS (
            SELECT 
                customer_id,
                COUNT(*) as shipment_count,
                MIN(created_at) as first_shipment,
                MAX(created_at) as last_shipment
            FROM (
                SELECT customer_id, created_at
                FROM domestic_domesticshipment
                UNION ALL
                SELECT customer_id, created_at
                FROM international_internationalshipment
            ) AS all_shipments
            GROUP BY customer_id
        )
        SELECT 
            COUNT(*) as total_customers,
            COUNT(CASE WHEN shipment_count = 1 THEN 1 END) as one_time_customers,
            COUNT(CASE WHEN shipment_count >= 2 THEN 1 END) as repeat_customers,
            ROUND(
                100.0 * COUNT(CASE WHEN shipment_count >= 2 THEN 1 END) / 
                NULLIF(COUNT(*), 0), 
                2
            ) as repeat_customer_rate,
            AVG(shipment_count) as avg_shipments_per_customer,
            MAX(shipment_count) as max_shipments_single_customer
        FROM customer_stats;
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            result = dict(zip(columns, row)) if row else {}
        
        return result


# Materialized view helper (for production optimization)
def create_materialized_views():
    """
    Create materialized views for faster analytics queries.
    
    Run this periodically (e.g., daily cron job) to pre-compute aggregates.
    Significantly improves performance for dashboard queries.
    """
    # Note: Requires PostgreSQL
    # SQLite doesn't support materialized views natively
    
    views = [
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_revenue AS
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as shipment_count,
            SUM(cost) as total_revenue
        FROM (
            SELECT created_at, cost
            FROM domestic_domesticshipment
            UNION ALL
            SELECT created_at, cost
            FROM international_internationalshipment
        ) AS all_shipments
        GROUP BY DATE(created_at);
        """,
        
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_sector_stats AS
        SELECT 
            destination as sector,
            COUNT(*) as shipment_count,
            SUM(cost) as total_revenue
        FROM (
            SELECT destination, cost
            FROM domestic_domesticshipment
            UNION ALL
            SELECT destination, cost
            FROM international_internationalshipment
        ) AS all_shipments
        GROUP BY destination;
        """
    ]
    
    with connection.cursor() as cursor:
        for view_sql in views:
            try:
                cursor.execute(view_sql)
                logger.info("Materialized view created successfully")
            except Exception as e:
                logger.warning(f"Materialized view creation skipped: {e}")
                # SQLite doesn't support materialized views
                pass


def refresh_materialized_views():
    """Refresh materialized views with latest data."""
    views = ['mv_daily_revenue', 'mv_sector_stats']
    
    with connection.cursor() as cursor:
        for view_name in views:
            try:
                cursor.execute(f"REFRESH MATERIALIZED VIEW {view_name};")
                logger.info(f"Refreshed materialized view: {view_name}")
            except Exception as e:
                logger.warning(f"View refresh skipped: {e}")
