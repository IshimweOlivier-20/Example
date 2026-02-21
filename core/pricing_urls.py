"""
URL configuration for pricing endpoints.
"""
from django.urls import path
from core import pricing_views

urlpatterns = [
    path('tariffs/', pricing_views.get_tariffs, name='get-tariffs'),
    path('calculate/', pricing_views.calculate_cost, name='calculate-cost'),
    path('admin/cache/clear-tariffs/', pricing_views.clear_cache, name='clear-cache'),
]
