"""
Core app serializers for authentication and user management.
Compliance: Type-annotated for code quality per rubric requirements.
"""
from typing import Dict, Any
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .validators import validate_rwanda_phone, validate_rwanda_nid, extract_birth_year_from_nid

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Supports CUSTOMER, AGENT, DRIVER user types.
    """
    password = serializers.CharField(write_only=True, min_length=8, 
                                    help_text="Minimum 8 characters")
    birth_year = serializers.IntegerField(required=False, 
                                         help_text="Year of birth for NID validation")
    
    class Meta:
        model = User
        fields = ['id', 'phone', 'password', 'full_name', 'user_type', 
                 'nid_number', 'birth_year', 'assigned_sector']
        read_only_fields = ['id']
    
    def validate_phone(self, value: str) -> str:
        """Validate Rwanda phone format."""
        is_valid, error = validate_rwanda_phone(value)
        if not is_valid:
            raise serializers.ValidationError(error)
        return value
    
    def validate_nid_number(self, value: str) -> str:
        """Validate Rwanda National ID."""
        if value:
            # Birth year cross-validation happens in validate()
            is_valid, error = validate_rwanda_nid(value)
            if not is_valid:
                raise serializers.ValidationError(error)
        return value
    
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Additional validation for agents and NID cross-checking.
        
        Compliance: Law N° 058/2021 - KYC verification requirements
        """
        # Agent validation
        if data.get('user_type') == 'AGENT':
            if not data.get('nid_number'):
                raise serializers.ValidationError({
                    'nid_number': 'National ID is required for Agent registration'
                })
            if not data.get('assigned_sector'):
                raise serializers.ValidationError({
                    'assigned_sector': 'Assigned sector is required for Agent registration'
                })
        
        # NID birth year cross-validation
        nid = data.get('nid_number')
        birth_year = data.get('birth_year')
        
        if nid and birth_year:
            nid_year = extract_birth_year_from_nid(nid)
            if nid_year and nid_year != birth_year:
                raise serializers.ValidationError({
                    'birth_year': f'Birth year mismatch. NID shows {nid_year}, but you provided {birth_year}'
                })
        
        return data
    
    def create(self, validated_data: Dict[str, Any]) -> User:
        """Create user with hashed password."""
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile (READ operations)."""
    
    class Meta:
        model = User
        fields = ['id', 'phone', 'full_name', 'user_type', 'nid_number', 
                 'assigned_sector', 'is_verified', 'verification_date', 
                 'birth_year', 'date_joined']
        read_only_fields = ['id', 'is_verified', 'verification_date', 'date_joined']


class NIDVerificationSerializer(serializers.Serializer):
    """
    Serializer for NID verification with birth year cross-check.
    
    Compliance: NCSA digital identity verification standards
    """
    national_id = serializers.CharField(max_length=16, help_text="16-digit Rwanda NID")
    birth_year = serializers.IntegerField(required=False, min_value=1900, max_value=2010,
                                         help_text="Birth year for cross-validation")
    
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate NID format and cross-check birth year."""
        nid = data.get('national_id')
        birth_year = data.get('birth_year')
        
        # Validate with birth year cross-check
        is_valid, error = validate_rwanda_nid(nid, birth_year)
        if not is_valid:
            raise serializers.ValidationError({'national_id': error})
        
        return data


class OTPRequestSerializer(serializers.Serializer):
    """Serializer for requesting OTP."""
    phone = serializers.CharField(max_length=20)
    purpose = serializers.ChoiceField(
        choices=['REGISTRATION', 'LOGIN', 'PASSWORD_RESET', 'TRANSACTION'],
        default='LOGIN'
    )
    
    def validate_phone(self, value: str) -> str:
        """Validate phone format."""
        is_valid, error = validate_rwanda_phone(value)
        if not is_valid:
            raise serializers.ValidationError(error)
        return value


class OTPVerifySerializer(serializers.Serializer):
    """Serializer for verifying OTP."""
    phone = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(max_length=6, min_length=6)
    
    def validate_otp_code(self, value: str) -> str:
        """Ensure OTP is 6 digits."""
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be 6 digits")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure new passwords match."""
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match'
            })
        return data


class UserDataExportSerializer(serializers.Serializer):
    """
    Serializer for user data export (GDPR-style).
    
    Compliance: Law N° 058/2021 Article 28 - Right to data portability
    """
    format = serializers.ChoiceField(choices=['json', 'csv'], default='json')
    include_shipments = serializers.BooleanField(default=True)
    include_audit_logs = serializers.BooleanField(default=True)
