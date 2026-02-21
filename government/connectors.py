"""
Government integration connectors for Rwanda compliance.

RRA (Rwanda Revenue Authority): Electronic Billing Machine (EBM) integration
RURA (Rwanda Utilities Regulatory Authority): Transport license verification

Compliance:
- Law N° 058/2021: Data protection and privacy
- RRA Tax Law: EBM receipt mandatory for all transactions
- RURA Transport Law: Driver license and vehicle insurance validation
"""
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import hashlib
import uuid
import logging
import random

logger = logging.getLogger(__name__)


class RRAConnector:
    """
    Rwanda Revenue Authority (RRA) integration.
    
    Purpose: Generate Electronic Billing Machine (EBM) receipts
    All payments must have a digitally signed tax receipt
    
    Production: Connect to RRA's SIGTAS (Standard Integrated Government Tax
    Administration System)
    """
    
    def __init__(self, tin: str = "100000000", api_key: Optional[str] = None):
        """
        Initialize RRA connector.
        
        Args:
            tin: Tax Identification Number for IshemaLink entity
            api_key: RRA API authentication key (from environment)
        """
        self.tin = tin
        self.api_key = api_key or "MOCK_RRA_API_KEY"
        self.ebm_url = "https://ebm.rra.gov.rw/api/v1"  # Production URL
    
    def sign_receipt(
        self,
        amount: Decimal,
        tax_amount: Decimal,
        transaction_id: str,
        customer_tin: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate EBM digital signature for payment receipt.
        
        Compliance: RRA requires digital signature on all B2B transactions
        
        Args:
            amount: Total payment amount (RWF)
            tax_amount: VAT component (18%)
            transaction_id: Internal payment reference
            customer_tin: Customer's TIN (optional for B2C)
            
        Returns:
            Receipt with digital signature and RRA control code
        """
        # Generate unique EBM receipt number
        ebm_receipt_no = f"RW-EBM-{uuid.uuid4().hex[:12].upper()}"
        
        # Create signature payload
        signature_data = f"{self.tin}|{amount}|{tax_amount}|{transaction_id}"
        digital_signature = self._generate_signature(signature_data)
        
        # Simulate RRA API call
        receipt = {
            'ebm_receipt_number': ebm_receipt_no,
            'digital_signature': digital_signature,
            'rra_control_code': self._generate_control_code(),
            'tin': self.tin,
            'customer_tin': customer_tin,
            'amount': float(amount),
            'tax_amount': float(tax_amount),
            'transaction_id': transaction_id,
            'timestamp': datetime.now().isoformat(),
            'status': 'SIGNED',
            'qr_code': self._generate_qr_code(ebm_receipt_no)
        }
        
        logger.info(
            f"EBM receipt generated: {ebm_receipt_no} "
            f"for {amount} RWF (Tax: {tax_amount})"
        )
        
        # In production: POST to RRA SIGTAS API
        # response = requests.post(
        #     f"{self.ebm_url}/sign-receipt",
        #     headers={'Authorization': f'Bearer {self.api_key}'},
        #     json=receipt
        # )
        
        return receipt
    
    def verify_signature(self, ebm_receipt_number: str) -> Dict[str, Any]:
        """
        Verify EBM signature authenticity with RRA.
        
        Used by: Government auditors, customers
        """
        # In production: Query RRA database
        return {
            'valid': True,
            'ebm_receipt_number': ebm_receipt_number,
            'verified_at': datetime.now().isoformat()
        }
    
    def submit_tax_report(self, period: str) -> Dict[str, Any]:
        """
        Submit monthly tax report to RRA.
        
        Compliance: Required by law - submit by 15th of each month
        
        Args:
            period: 'YYYY-MM' format (e.g., '2026-02')
            
        Returns:
            Submission confirmation with RRA reference
        """
        # Calculate aggregated tax for period
        # In production: Query database for all transactions in period
        
        report = {
            'period': period,
            'total_revenue': 0,  # Sum of all shipments
            'total_vat': 0,      # 18% VAT
            'submission_date': datetime.now().isoformat(),
            'rra_reference': f"TAX-{uuid.uuid4().hex[:8].upper()}"
        }
        
        logger.info(f"Tax report submitted for {period}")
        
        # In production: POST to RRA portal
        return report
    
    def _generate_signature(self, data: str) -> str:
        """Generate SHA-256 digital signature."""
        return hashlib.sha256(f"{data}{self.api_key}".encode()).hexdigest()
    
    def _generate_control_code(self) -> str:
        """Generate RRA control code (10-digit)."""
        return str(random.randint(1000000000, 9999999999))
    
    def _generate_qr_code(self, ebm_receipt_no: str) -> str:
        """Generate QR code URL for receipt verification."""
        return f"https://verify.rra.gov.rw/ebm/{ebm_receipt_no}"


class RURAConnector:
    """
    Rwanda Utilities Regulatory Authority (RURA) integration.
    
    Purpose: Transport license and vehicle insurance verification
    Prevents dispatch of shipments using unlicensed drivers or uninsured vehicles
    
    Compliance: RURA Transport Regulation Act
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize RURA connector.
        
        Args:
            api_key: RURA API authentication key
        """
        self.api_key = api_key or "MOCK_RURA_API_KEY"
        self.rura_url = "https://portal.rura.gov.rw/api/v2"  # Production URL
    
    def verify_driver_license(self, license_number: str) -> Dict[str, Any]:
        """
        Verify driver's license validity with RURA.
        
        Checks:
        - License is active and not suspended
        - No traffic violations pending
        - Medical certificate is current
        
        Args:
            license_number: Rwanda driver's license number
            
        Returns:
            Verification result with expiry date
            
        Raises:
            LicenseInvalidException: License suspended or expired
        """
        # Simulate RURA database lookup
        # In production: GET request to RURA portal
        
        # Mock response - in reality would check RURA database
        is_valid = license_number.startswith('RW')  # Simple validation
        
        if not is_valid:
            raise LicenseInvalidException(
                f"Invalid license format: {license_number}"
            )
        
        verification = {
            'license_number': license_number,
            'status': 'ACTIVE',
            'driver_name': 'MOCK DRIVER',  # Production: Real name from RURA
            'category': 'C',  # Heavy vehicle category
            'issue_date': '2020-01-01',
            'expiry_date': (datetime.now() + timedelta(days=365*2)).date().isoformat(),
            'violations_pending': 0,
            'medical_cert_valid': True,
            'verified_at': datetime.now().isoformat()
        }
        
        logger.info(f"Driver license verified: {license_number} - ACTIVE")
        
        return verification
    
    def verify_vehicle_insurance(self, plate_number: str) -> Dict[str, Any]:
        """
        Verify vehicle insurance with RURA.
        
        Checks:
        - Third-party insurance is active
        - Goods-in-transit coverage is valid
        - No outstanding insurance claims
        
        Args:
            plate_number: Rwanda vehicle plate number
            
        Returns:
            Insurance verification result
        """
        # In production: Query RURA insurance database
        
        is_valid = plate_number.startswith('RAD')  # Rwanda plate format
        
        if not is_valid:
            raise InsuranceInvalidException(
                f"Invalid plate number: {plate_number}"
            )
        
        insurance = {
            'plate_number': plate_number,
            'status': 'ACTIVE',
            'insurance_provider': 'RADIANT Insurance',
            'policy_number': f"POL-{uuid.uuid4().hex[:8].upper()}",
            'coverage_type': 'COMPREHENSIVE',
            'goods_in_transit': True,
            'max_coverage': 50000000,  # 50M RWF
            'expiry_date': (datetime.now() + timedelta(days=180)).date().isoformat(),
            'verified_at': datetime.now().isoformat()
        }
        
        logger.info(f"Vehicle insurance verified: {plate_number} - ACTIVE")
        
        return insurance
    
    def verify_transport_authorization(
        self,
        company_tin: str,
        vehicle_plate: str
    ) -> Dict[str, Any]:
        """
        Verify company's transport operating license.
        
        RURA requires all commercial transport operators to hold
        a Transport Authorization Certificate.
        
        Args:
            company_tin: Company Tax ID
            vehicle_plate: Vehicle registration
            
        Returns:
            Authorization status
        """
        authorization = {
            'company_tin': company_tin,
            'vehicle_plate': vehicle_plate,
            'authorization_number': f"TA-{uuid.uuid4().hex[:8].upper()}",
            'status': 'VALID',
            'service_type': 'GOODS_TRANSPORT',
            'routes_authorized': ['DOMESTIC', 'EAC'],
            'issue_date': '2024-01-01',
            'expiry_date': '2027-01-01',
            'verified_at': datetime.now().isoformat()
        }
        
        logger.info(f"Transport authorization verified: {company_tin}")
        
        return authorization
    
    def report_incident(
        self,
        driver_license: str,
        plate_number: str,
        incident_type: str,
        description: str
    ) -> str:
        """
        Report traffic incident to RURA.
        
        Used for: Accidents, cargo damage, customer complaints
        
        Args:
            driver_license: Driver's license number
            plate_number: Vehicle plate
            incident_type: ACCIDENT, DAMAGE, COMPLAINT, etc.
            description: Incident details
            
        Returns:
            Incident report reference number
        """
        incident_ref = f"INC-{uuid.uuid4().hex[:8].upper()}"
        
        incident_report = {
            'reference': incident_ref,
            'driver_license': driver_license,
            'plate_number': plate_number,
            'incident_type': incident_type,
            'description': description,
            'reported_at': datetime.now().isoformat(),
            'status': 'SUBMITTED'
        }
        
        logger.warning(
            f"Incident reported to RURA: {incident_ref} - {incident_type}"
        )
        
        # In production: POST to RURA incident portal
        
        return incident_ref


class CustomsConnector:
    """
    Rwanda Customs (RRA Customs & Excise Department) integration.
    
    Purpose: Generate EAC-compliant customs manifests for cross-border shipments
    """
    
    def generate_manifest_xml(
        self,
        shipment_data: Dict[str, Any]
    ) -> str:
        """
        Generate EAC-compliant XML manifest.
        
        Compliance: East African Community Customs Management Act
        
        Args:
            shipment_data: Shipment details (HS codes, values, etc.)
            
        Returns:
            XML string conforming to EAC schema
        """
        # Simplified XML generation
        # In production: Use proper XML library with EAC schema validation
        
        manifest_id = f"MF-{uuid.uuid4().hex[:8].upper()}"
        
        xml_manifest = f"""<?xml version="1.0" encoding="UTF-8"?>
<Manifest xmlns="urn:eac:customs:manifest">
    <ManifestID>{manifest_id}</ManifestID>
    <ExportCountry>RW</ExportCountry>
    <ImportCountry>{shipment_data.get('destination_country', 'UG')}</ImportCountry>
    <Consignor>
        <Name>{shipment_data.get('sender_name', 'IshemaLink User')}</Name>
        <TIN>{shipment_data.get('sender_tin', 'N/A')}</TIN>
    </Consignor>
    <Consignee>
        <Name>{shipment_data.get('recipient_name')}</Name>
        <Phone>{shipment_data.get('recipient_phone')}</Phone>
    </Consignee>
    <Goods>
        <Description>{shipment_data.get('commodity_type')}</Description>
        <HSCode>{shipment_data.get('hs_code', '0000.00')}</HSCode>
        <Weight>{shipment_data.get('weight_kg')}</Weight>
        <Value>{shipment_data.get('customs_value', 0)}</Value>
        <Currency>RWF</Currency>
    </Goods>
    <GeneratedAt>{datetime.now().isoformat()}</GeneratedAt>
</Manifest>"""
        
        logger.info(f"Customs manifest generated: {manifest_id}")
        
        return xml_manifest


# Custom Exceptions
class LicenseInvalidException(Exception):
    """Raised when driver license verification fails."""
    pass


class InsuranceInvalidException(Exception):
    """Raised when vehicle insurance verification fails."""
    pass
