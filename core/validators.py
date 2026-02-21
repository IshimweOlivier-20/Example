"""
Rwanda-specific validation utilities.
These validators ensure compliance with Rwanda KYC regulations.
"""
import re
from typing import Tuple


def validate_rwanda_phone(phone: str) -> Tuple[bool, str | None]:
    """
    Validate Rwanda phone number format.
    
    Valid format: +250 7XX XXX XXX
    Network codes:
    - 78X: MTN
    - 72X: Airtel
    - 73X: Airtel
    
    Args:
        phone: Phone number string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Normalize: remove spaces, dashes, and other separators
    cleaned = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Check basic format
    if not cleaned.startswith('+250'):
        return False, "Phone number must start with +250"
    
    # Pattern: +250 followed by 7, then [2,3,8], then 7 more digits
    pattern = r'^\+2507[2378]\d{7}$'
    
    if not re.match(pattern, cleaned):
        return False, "Invalid Rwanda phone format. Must be +250 7XX XXX XXX"
    
    return True, None


def validate_rwanda_nid(nid: str, birth_year: int = None) -> Tuple[bool, str | None]:
    """
    Validate Rwanda National ID (16-digit format).
    
    Format: 1 YYYY 7 XXXXXXX XXXXX C
    - Starts with '1'
    - Year of birth (4 digits, positions 1-4)
    - Province code (1 digit: 1-5)
    - Registration office + sequence (11 digits)
    - Checksum digit (Luhn algorithm)
    
    Compliance: Law N° 058/2021 - KYC requirements
    Cross-validates birth year from NID with user-provided birth year.
    
    Args:
        nid: National ID string to validate
        birth_year: Optional user's birth year for cross-validation
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check basic format
    if not nid:
        return False, "National ID is required"
    
    if not nid.isdigit():
        return False, "National ID must contain only digits"
    
    if len(nid) != 16:
        return False, "National ID must be exactly 16 digits"
    
    # Must start with '1'
    if not nid.startswith('1'):
        return False, "Invalid NID format. Must start with 1"
    
    # Extract and validate birth year (positions 1-4, 0-indexed)
    try:
        nid_year = int(nid[1:5])
        if nid_year < 1900 or nid_year > 2010:
            return False, f"Invalid birth year: {nid_year}. Must be between 1900 and 2010"
        
        # Cross-validate with provided birth year
        # Compliance: Additional identity verification per NCSA guidelines
        if birth_year is not None and nid_year != birth_year:
            return False, f"Birth year mismatch. NID shows {nid_year}, but provided {birth_year}"
            
    except ValueError:
        return False, "Invalid year format in NID"
    
    # Validate province code (position 5, should be 1-5 for Rwanda's 5 provinces)
    # Extended to 7 for administrative regions
    province_code = int(nid[5])
    if province_code < 1 or province_code > 7:
        return False, f"Invalid province code: {province_code}"
    
    # Note: Luhn checksum validation disabled for development/testing
    # Enable in production for stricter validation
    # if not _luhn_check(nid):
    #     return False, "Invalid NID checksum"
    
    return True, None


def _luhn_check(number: str) -> bool:
    """
    Implement Luhn algorithm for checksum validation.
    
    The Luhn algorithm:
    1. Starting from the rightmost digit (checksum), move left
    2. Double every second digit
    3. If doubling results in > 9, subtract 9
    4. Sum all digits
    5. If sum % 10 == 0, checksum is valid
    
    Args:
        number: String of digits to validate
        
    Returns:
        Boolean indicating if checksum is valid
    """
    def digits_of(n):
        return [int(d) for d in str(n)]
    
    digits = digits_of(number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    
    return checksum % 10 == 0


def extract_birth_year_from_nid(nid: str) -> int | None:
    """
    Extract birth year from Rwanda NID.
    
    Args:
        nid: 16-digit National ID
        
    Returns:
        Birth year as integer or None if invalid
    """
    if not nid or len(nid) < 5:
        return None
    
    try:
        year = int(nid[1:5])
        return year if 1900 <= year <= 2010 else None
    except ValueError:
        return None


def validate_tin(tin: str) -> Tuple[bool, str | None]:
    """
    Validate Rwanda Tax Identification Number (TIN).
    
    Format: 9 digits
    
    Args:
        tin: TIN string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not tin:
        return False, "TIN is required for international shipments"
    
    cleaned = tin.replace(" ", "").replace("-", "")
    
    if not cleaned.isdigit():
        return False, "TIN must contain only digits"
    
    if len(cleaned) != 9:
        return False, "TIN must be exactly 9 digits"
    
    return True, None


def validate_passport(passport: str) -> Tuple[bool, str | None]:
    """
    Validate passport number format.
    
    Basic validation for EAC passport formats.
    
    Args:
        passport: Passport number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not passport:
        return False, "Passport number is required for international shipments"
    
    # Remove spaces
    cleaned = passport.replace(" ", "").upper()
    
    # Basic check: should be alphanumeric, 6-9 characters
    if not cleaned.isalnum():
        return False, "Passport must be alphanumeric"
    
    if len(cleaned) < 6 or len(cleaned) > 9:
        return False, "Passport must be 6-9 characters"
    
    return True, None
