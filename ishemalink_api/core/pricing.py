"""
Pricing and tariff caching utilities.
"""
from typing import Dict, Optional
from decimal import Decimal
from django.core.cache import cache
from django.conf import settings
from core.models import ShippingZone


def get_zone_for_destination(destination: str) -> str:
    """
    Determine shipping zone based on destination.
    
    Args:
        destination: Destination name or address
        
    Returns:
        Zone code (ZONE_1, ZONE_2, or ZONE_3)
    """
    destination_lower = destination.lower()
    
    # Zone 1: Kigali
    kigali_areas = ['kigali', 'gasabo', 'kicukiro', 'nyarugenge']
    if any(area in destination_lower for area in kigali_areas):
        return 'ZONE_1'
    
    # Zone 3: EAC countries
    eac_countries = ['kampala', 'uganda', 'nairobi', 'kenya', 'goma', 'drc', 'tanzania', 'burundi']
    if any(country in destination_lower for country in eac_countries):
        return 'ZONE_3'
    
    # Zone 2: Other Rwanda provinces
    return 'ZONE_2'


def get_cached_tariffs(zone_code: str) -> Optional[Dict]:
    """
    Get tariffs from cache or database.
    
    Args:
        zone_code: Zone code (ZONE_1, ZONE_2, ZONE_3)
        
    Returns:
        Dictionary with tariff information or None
    """
    cache_key = f"tariff:zone:{zone_code}:v1"
    
    # Try cache first
    cached_data = cache.get(cache_key)
    if cached_data:
        cached_data['cache_hit'] = True
        return cached_data
    
    # Cache miss - fetch from database
    try:
        zone = ShippingZone.objects.get(code=zone_code)
        
        tariff_data = {
            'code': zone.code,
            'name': zone.name,
            'base_rate': float(zone.base_rate),
            'per_kg_rate': float(zone.per_kg_rate),
            'description': zone.description,
            'cache_hit': False
        }
        
        # Store in cache
        cache.set(cache_key, tariff_data, timeout=settings.CACHE_TTL_TARIFFS)
        
        return tariff_data
        
    except ShippingZone.DoesNotExist:
        return None


def calculate_shipping_cost(destination: str, weight_kg: Decimal) -> Dict:
    """
    Calculate shipping cost based on destination and weight.
    
    Args:
        destination: Destination location
        weight_kg: Package weight in kilograms
        
    Returns:
        Dictionary with cost breakdown
    """
    zone_code = get_zone_for_destination(destination)
    tariff = get_cached_tariffs(zone_code)
    
    if not tariff:
        raise ValueError(f"Tariff not found for zone: {zone_code}")
    
    base_rate = Decimal(str(tariff['base_rate']))
    per_kg_rate = Decimal(str(tariff['per_kg_rate']))
    
    # Calculate total cost
    weight_cost = per_kg_rate * weight_kg
    total_cost = base_rate + weight_cost
    
    return {
        'zone': zone_code,
        'zone_name': tariff['name'],
        'base_rate': float(base_rate),
        'per_kg_rate': float(per_kg_rate),
        'weight_kg': float(weight_kg),
        'weight_cost': float(weight_cost),
        'total_cost': float(total_cost),
        'cache_hit': tariff.get('cache_hit', False)
    }


def clear_tariff_cache() -> int:
    """
    Clear all tariff caches.
    
    Returns:
        Number of cache keys cleared
    """
    zones = ['ZONE_1', 'ZONE_2', 'ZONE_3']
    cleared = 0
    
    for zone in zones:
        cache_key = f"tariff:zone:{zone}:v1"
        if cache.delete(cache_key):
            cleared += 1
    
    return cleared
