"""
URL configuration for international shipments.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('shipments/', views.InternationalShipmentListCreateView.as_view(), name='international-shipments'),
    path('shipments/<int:pk>/', views.InternationalShipmentDetailView.as_view(), name='international-shipment-detail'),
    path('customs-documents/', views.CustomsDocumentCreateView.as_view(), name='customs-document-create'),
]
