"""
URL configuration for billing app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('invoices/', views.InvoiceListView.as_view(), name='invoice-list'),
]
