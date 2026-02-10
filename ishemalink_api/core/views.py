"""
Core app views for authentication and user management.
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from .serializers import UserRegistrationSerializer, UserSerializer, NIDVerificationSerializer
from .validators import validate_rwanda_nid

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Register a new user (Customer or Agent).
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'id': user.id,
            'phone': user.phone,
            'role': user.user_type,
            'assigned_sector': user.assigned_sector,
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_nid(request):
    """
    POST /api/auth/verify-nid/
    Standalone NID validation endpoint.
    """
    serializer = NIDVerificationSerializer(data=request.data)
    
    if serializer.is_valid():
        return Response({
            'valid': True,
            'national_id': serializer.validated_data['national_id']
        })
    else:
        # Extract the error message
        error_msg = serializer.errors.get('national_id', ['Invalid NID format'])[0]
        return Response({
            'valid': False,
            'error': str(error_msg)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    GET /api/users/me/
    Get current user profile.
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def agent_onboarding(request):
    """
    POST /api/users/agents/onboard/
    Special endpoint for Agent onboarding with additional verification.
    """
    # Force user_type to AGENT
    data = request.data.copy()
    data['user_type'] = 'AGENT'
    
    serializer = UserRegistrationSerializer(data=data)
    
    if serializer.is_valid():
        # Create agent but set is_active=False pending admin approval
        user = serializer.save()
        user.is_active = False
        user.save()
        
        return Response({
            'id': user.id,
            'phone': user.phone,
            'role': user.user_type,
            'assigned_sector': user.assigned_sector,
            'status': 'pending_approval',
            'message': 'Agent account created. Awaiting admin approval.'
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
