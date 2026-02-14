"""
Billing views for invoices and payments.
"""
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Invoice
from .serializers import InvoiceSerializer


class InvoiceListView(generics.ListAPIView):
    """
    GET /api/billing/invoices/
    List invoices for the current user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        return Invoice.objects.filter(customer=self.request.user)
