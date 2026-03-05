import pytest
from decimal import Decimal
from django.core.cache import cache
from core.models import ShippingZone
from core.pricing import (
    get_zone_for_destination,
    get_cached_tariffs,
    calculate_shipping_cost,
    clear_tariff_cache
)


@pytest.mark.django_db
class TestPricingComplete:
    def setup_method(self):
        cache.clear()
        ShippingZone.objects.all().delete()
        ShippingZone.objects.create(
            code='ZONE_1',
            name='Kigali',
            base_rate=Decimal('1500'),
            per_kg_rate=Decimal('200'),
            description='Kigali metropolitan area'
        )
        ShippingZone.objects.create(
            code='ZONE_2',
            name='Provinces',
            base_rate=Decimal('3000'),
            per_kg_rate=Decimal('300'),
            description='Other Rwanda provinces'
        )
        ShippingZone.objects.create(
            code='ZONE_3',
            name='EAC Countries',
            base_rate=Decimal('15000'),
            per_kg_rate=Decimal('500'),
            description='East African Community'
        )
    
    def test_zone_kigali(self):
        assert get_zone_for_destination('Kigali') == 'ZONE_1'
        assert get_zone_for_destination('kigali') == 'ZONE_1'
        assert get_zone_for_destination('KIGALI') == 'ZONE_1'
    
    def test_zone_kigali_districts(self):
        assert get_zone_for_destination('Gasabo') == 'ZONE_1'
        assert get_zone_for_destination('Kicukiro') == 'ZONE_1'
        assert get_zone_for_destination('Nyarugenge') == 'ZONE_1'
    
    def test_zone_eac_uganda(self):
        assert get_zone_for_destination('Kampala') == 'ZONE_3'
        assert get_zone_for_destination('Uganda') == 'ZONE_3'
    
    def test_zone_eac_kenya(self):
        assert get_zone_for_destination('Nairobi') == 'ZONE_3'
        assert get_zone_for_destination('Kenya') == 'ZONE_3'
    
    def test_zone_eac_drc(self):
        assert get_zone_for_destination('Goma') == 'ZONE_3'
        assert get_zone_for_destination('DRC') == 'ZONE_3'
    
    def test_zone_eac_tanzania(self):
        assert get_zone_for_destination('Tanzania') == 'ZONE_3'
    
    def test_zone_eac_burundi(self):
        assert get_zone_for_destination('Burundi') == 'ZONE_3'
    
    def test_zone_provinces(self):
        assert get_zone_for_destination('Huye') == 'ZONE_2'
        assert get_zone_for_destination('Musanze') == 'ZONE_2'
        assert get_zone_for_destination('Rubavu') == 'ZONE_2'
    
    def test_cached_tariffs_cache_miss(self):
        cache.clear()
        tariff = get_cached_tariffs('ZONE_1')
        assert tariff is not None
        assert tariff['code'] == 'ZONE_1'
        assert tariff['cache_hit'] is False
    
    def test_cached_tariffs_cache_hit(self):
        cache.clear()
        get_cached_tariffs('ZONE_1')
        tariff = get_cached_tariffs('ZONE_1')
        assert tariff['cache_hit'] is True
    
    def test_cached_tariffs_not_found(self):
        tariff = get_cached_tariffs('ZONE_99')
        assert tariff is None
    
    def test_calculate_cost_zone1(self):
        result = calculate_shipping_cost('Kigali', Decimal('5.0'))
        assert result['zone'] == 'ZONE_1'
        assert result['total_cost'] == 2500.0
        assert result['base_rate'] == 1500.0
        assert result['per_kg_rate'] == 200.0
    
    def test_calculate_cost_zone2(self):
        result = calculate_shipping_cost('Huye', Decimal('10.0'))
        assert result['zone'] == 'ZONE_2'
        assert result['total_cost'] == 6000.0
    
    def test_calculate_cost_zone3(self):
        result = calculate_shipping_cost('Kampala', Decimal('20.0'))
        assert result['zone'] == 'ZONE_3'
        assert result['total_cost'] == 25000.0
    
    def test_calculate_cost_with_cache(self):
        calculate_shipping_cost('Kigali', Decimal('5.0'))
        result = calculate_shipping_cost('Kigali', Decimal('10.0'))
        assert result['cache_hit'] is True
    
    def test_calculate_cost_invalid_zone(self):
        ShippingZone.objects.filter(code='ZONE_2').delete()
        cache.clear()
        with pytest.raises(ValueError, match='Tariff not found'):
            calculate_shipping_cost('Huye', Decimal('5.0'))
    
    def test_clear_tariff_cache(self):
        get_cached_tariffs('ZONE_1')
        get_cached_tariffs('ZONE_2')
        cleared = clear_tariff_cache()
        assert cleared >= 0
