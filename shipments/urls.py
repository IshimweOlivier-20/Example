"""
URL configuration for shipments app (shared tracking endpoints).
Routes map to domestic shipment handlers to satisfy shared endpoints.
"""
from django.urls import path
from domestic import views as domestic_views

urlpatterns = [
    # Shared shipment routes
    path('', domestic_views.DomesticShipmentListCreateView.as_view(), name='shipments-list'),
    path('<int:pk>/', domestic_views.DomesticShipmentDetailView.as_view(), name='shipments-detail'),
    path('<int:pk>/update-status/', domestic_views.update_shipment_status, name='update-status'),
    path('batch-update/', domestic_views.batch_update_status, name='batch-update'),
    path('<int:pk>/tracking/', domestic_views.get_tracking_history, name='tracking-history'),
]
