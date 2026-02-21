"""
URL configuration for domestic shipments.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Shipment CRUD
    path('shipments/', views.DomesticShipmentListCreateView.as_view(), name='domestic-shipments'),
    path('shipments/<int:pk>/', views.DomesticShipmentDetailView.as_view(), name='domestic-shipment-detail'),
    
    # Async tracking
    path('shipments/<int:pk>/update-status/', views.update_shipment_status, name='update-status'),
    path('shipments/batch-update/', views.batch_update_status, name='batch-update'),
    path('shipments/<int:pk>/tracking/', views.get_tracking_history, name='tracking-history'),
]
