import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from decimal import Decimal

from core.models import ShippingZone

User = get_user_model()


@pytest.mark.django_db
class TestOpsViews:
    def setup_method(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            phone='+250788999999',
            password='admin123',
            user_type='ADMIN'
        )

    def test_deep_health_check(self):
        response = self.client.get('/api/health/deep/')
        assert response.status_code in [200, 503]
        assert 'status' in response.data

    def test_prometheus_metrics(self):
        response = self.client.get('/api/ops/metrics/')
        assert response.status_code == 200

    def test_maintenance_toggle_unauthorized(self):
        response = self.client.post('/api/ops/maintenance/toggle/', {
            'enabled': True
        })
        assert response.status_code == 401

    def test_maintenance_toggle_authorized(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/ops/maintenance/toggle/', {
            'enabled': True
        })
        assert response.status_code == 200

    def test_security_health_check(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/test/security-health/')
        assert response.status_code == 200
        assert 'debug_mode' in response.data


@pytest.mark.django_db
class TestGovernmentConnectors:
    @patch('government.connectors.RRAConnector._generate_signature')
    @patch('government.connectors.RRAConnector._generate_control_code')
    def test_rra_sign_receipt(self, mock_control, mock_sig):
        from government.connectors import RRAConnector
        
        mock_sig.return_value = 'test_signature_123'
        mock_control.return_value = '1234567890'
        
        rra = RRAConnector(tin='100000000')
        receipt = rra.sign_receipt(
            amount=Decimal('5000'),
            tax_amount=Decimal('900'),
            transaction_id='TXN123'
        )
        
        assert receipt['status'] == 'SIGNED'
        assert 'ebm_receipt_number' in receipt
        assert receipt['digital_signature'] == 'test_signature_123'

    def test_rra_verify_signature(self):
        from government.connectors import RRAConnector
        
        rra = RRAConnector()
        result = rra.verify_signature('RW-EBM-123456')
        assert result['valid'] is True

    def test_rra_submit_tax_report(self):
        from government.connectors import RRAConnector
        
        rra = RRAConnector()
        report = rra.submit_tax_report('2026-02')
        assert 'rra_reference' in report
        assert report['period'] == '2026-02'

    def test_rura_verify_driver_license_valid(self):
        from government.connectors import RURAConnector
        
        rura = RURAConnector()
        result = rura.verify_driver_license('RW123456')
        assert result['status'] == 'ACTIVE'

    def test_rura_verify_driver_license_invalid(self):
        from government.connectors import RURAConnector, LicenseInvalidException
        
        rura = RURAConnector()
        with pytest.raises(LicenseInvalidException):
            rura.verify_driver_license('INVALID')

    def test_rura_verify_vehicle_insurance_valid(self):
        from government.connectors import RURAConnector
        
        rura = RURAConnector()
        result = rura.verify_vehicle_insurance('RAD123A')
        assert result['status'] == 'ACTIVE'
        assert result['goods_in_transit'] is True

    def test_rura_verify_vehicle_insurance_invalid(self):
        from government.connectors import RURAConnector, InsuranceInvalidException
        
        rura = RURAConnector()
        with pytest.raises(InsuranceInvalidException):
            rura.verify_vehicle_insurance('INVALID')

    def test_rura_verify_transport_authorization(self):
        from government.connectors import RURAConnector
        
        rura = RURAConnector()
        result = rura.verify_transport_authorization('100000000', 'RAD123A')
        assert result['status'] == 'VALID'

    def test_rura_report_incident(self):
        from government.connectors import RURAConnector
        
        rura = RURAConnector()
        ref = rura.report_incident(
            driver_license='RW123456',
            plate_number='RAD123A',
            incident_type='ACCIDENT',
            description='Minor collision'
        )
        assert ref.startswith('INC-')

    def test_customs_generate_manifest(self):
        from government.connectors import CustomsConnector
        
        customs = CustomsConnector()
        xml = customs.generate_manifest_xml({
            'destination_country': 'UG',
            'sender_name': 'Test Sender',
            'sender_tin': '123456789',
            'recipient_name': 'Test Recipient',
            'recipient_phone': '+256700000000',
            'commodity_type': 'Coffee',
            'hs_code': '0901.21',
            'weight_kg': 100,
            'customs_value': 50000
        })
        assert '<?xml version' in xml
        assert '<Manifest' in xml
        assert 'Coffee' in xml
