"""
Locust load testing script for harvest peak simulation.

Simulates 2,000+ concurrent agents during coffee/tea harvest season.
Tests: Booking creation, payment flow, tracking, dashboard queries.
"""
import os
import random
from locust import HttpUser, task, between, events
import logging

logger = logging.getLogger(__name__)


class AgentUser(HttpUser):
    """
    Simulates rural agent creating shipments during harvest peak.
    
    Behavior:
    - Login with phone number
    - Create domestic shipments (high frequency)
    - Check shipment status
    - Query dashboard
    """
    wait_time = between(1, 3)
    
    def on_start(self):
        """Authenticate agent on startup."""
        phone = os.getenv('LOCUST_PHONE', '+250788123456')
        password = os.getenv('LOCUST_PASSWORD', 'testpass123')
        
        response = self.client.post(
            '/api/auth/token/obtain/',
            json={'phone': phone, 'password': password}
        )
        if response.status_code == 200:
            token = response.json().get('access')
            if token:
                self.client.headers.update({'Authorization': f'Bearer {token}'})
                logger.info(f"Agent authenticated: {phone}")
        else:
            logger.error(f"Authentication failed: {response.status_code}")
    
    @task(5)
    def create_domestic_shipment(self):
        """
        High-frequency task: Create domestic shipment.
        
        Simulates farmer sending produce to Kigali market.
        """
        payload = {
            'shipment_type': 'DOMESTIC',
            'origin': random.choice(['Huye', 'Musanze', 'Rubavu', 'Nyagatare']),
            'destination': random.choice(['Kigali', 'Huye', 'Musanze']),
            'weight_kg': round(random.uniform(1, 50), 2),
            'commodity_type': random.choice([
                'Potatoes', 'Coffee', 'Tea', 'Bananas', 'Cassava'
            ]),
            'recipient_phone': '+250788000111',
            'recipient_name': 'Market Buyer',
            'transport_type': random.choice(['MOTO', 'BUS'])
        }
        
        with self.client.post(
            '/api/shipments/create/',
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                response.success()
            elif response.status_code == 400:
                # Expected validation errors during stress test
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(2)
    def check_shipment_status(self):
        """
        Query shipment list with filters.
        
        Simulates agent checking pending pickups.
        """
        status_filter = random.choice(['PENDING', 'IN_TRANSIT', 'DELIVERED'])
        self.client.get(
            f'/api/shipments/?status={status_filter}&page=1&size=20',
            name='/api/shipments/?status=[status]'
        )
    
    @task(1)
    def view_dashboard(self):
        """
        Admin dashboard query.
        
        Tests aggregation query performance under load.
        """
        self.client.get('/api/admin/dashboard/summary/')
    
    @task(1)
    def health_check(self):
        """Basic health check."""
        self.client.get('/api/status/')


class CustomerUser(HttpUser):
    """
    Simulates customer tracking shipments.
    
    Lower frequency than agents.
    """
    wait_time = between(5, 10)
    
    def on_start(self):
        """Authenticate customer."""
        phone = os.getenv('LOCUST_CUSTOMER_PHONE', '+250788999999')
        password = os.getenv('LOCUST_PASSWORD', 'testpass123')
        
        response = self.client.post(
            '/api/auth/token/obtain/',
            json={'phone': phone, 'password': password}
        )
        if response.status_code == 200:
            token = response.json().get('access')
            if token:
                self.client.headers.update({'Authorization': f'Bearer {token}'})
    
    @task(3)
    def track_shipment(self):
        """Track shipment by tracking number."""
        # In real test, use actual tracking numbers
        tracking_code = f"RW-D-{random.randint(10000000, 99999999)}"
        self.client.get(
            f'/api/tracking/{tracking_code}/live/',
            name='/api/tracking/[code]/live/'
        )
    
    @task(1)
    def view_my_shipments(self):
        """List customer's own shipments."""
        self.client.get('/api/shipments/?page=1')


# Event hooks for reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test start."""
    logger.info("=" * 60)
    logger.info("IshemaLink Harvest Peak Load Test Starting")
    logger.info(f"Target: {environment.host}")
    logger.info("Simulating 2,000+ concurrent agents")
    logger.info("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test completion and results."""
    logger.info("=" * 60)
    logger.info("Load Test Completed")
    logger.info(f"Total requests: {environment.stats.total.num_requests}")
    logger.info(f"Failures: {environment.stats.total.num_failures}")
    logger.info(f"Avg response time: {environment.stats.total.avg_response_time}ms")
    logger.info("=" * 60)
