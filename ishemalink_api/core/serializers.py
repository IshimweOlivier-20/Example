"""
Core app serializers for authentication and user management.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .validators import validate_rwanda_phone, validate_rwanda_nid

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['id', 'phone', 'password', 'user_type', 'national_id', 'assigned_sector']
        read_only_fields = ['id']
    
    def validate_phone(self, value):
        """Validate Rwanda phone format."""
        is_valid, error = validate_rwanda_phone(value)
        if not is_valid:
            raise serializers.ValidationError(error)
        return value
    
    def validate_national_id(self, value):
        """Validate Rwanda National ID."""
        if value:
            is_valid, error = validate_rwanda_nid(value)
            if not is_valid:
                raise serializers.ValidationError(error)
        return value
    
    def validate(self, data):
        """Additional validation for agents."""
        if data.get('user_type') == 'AGENT':
            if not data.get('national_id'):
                raise serializers.ValidationError({
                    'national_id': 'National ID is required for Agent registration'
                })
            if not data.get('assigned_sector'):
                raise serializers.ValidationError({
                    'assigned_sector': 'Assigned sector is required for Agent registration'
                })
        return data
    
    def create(self, validated_data):
        """Create user with hashed password."""
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile."""
    
    class Meta:
        model = User
        fields = ['id', 'phone', 'user_type', 'national_id', 'assigned_sector', 'is_verified', 'date_joined']
        read_only_fields = ['id', 'is_verified', 'date_joined']


class NIDVerificationSerializer(serializers.Serializer):
    """Serializer for standalone NID verification."""
    national_id = serializers.CharField(max_length=16)
    
    def validate_national_id(self, value):
        """Validate NID format."""
        is_valid, error = validate_rwanda_nid(value)
        if not is_valid:
            raise serializers.ValidationError(error)
        return value
