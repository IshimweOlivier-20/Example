# Reflection: Domestic vs International Shipment Validation

## Introduction

In developing the IshemaLink API, one of the most critical architectural decisions was how to handle the fundamental differences between domestic shipments (within Rwanda) and international shipments (cross-border EAC trade). Rather than creating a monolithic shipment system with conditional logic, I implemented separate Django apps with distinct validation rules, data models, and business workflows.

## Regulatory Context

The primary driver for this separation stems from regulatory requirements. Domestic shipments operate entirely within Rwanda's borders and are subject to local Know Your Customer (KYC) regulations. This requires validation of Rwanda-specific identifiers: phone numbers in the +250 7XX XXX XXX format and 16-digit National IDs that follow a strict structure with Luhn checksum verification. These validations ensure compliance with Rwanda Revenue Authority (RRA) requirements for domestic commerce.

International shipments, however, cross into East African Community (EAC) partner nations and trigger customs clearance processes. Beyond the basic Rwanda KYC checks, these shipments require passport validation (6-9 alphanumeric characters), Tax Identification Numbers (9-digit TINs), commercial invoices, and certificates of origin. The regulatory burden is significantly higher because customs authorities in Uganda, Kenya, or DRC must verify the legitimacy of cross-border trade.

## Architectural Implementation

I implemented this distinction through separate Django apps: `domestic/` and `international/`. Each app contains its own models inheriting from a shared `BaseShipment` abstract class defined in the `core/` app. This inheritance structure allows both shipment types to share common fields (tracking number, customer, origin, destination, weight, cost, status) while extending with type-specific requirements.

The `DomesticShipment` model adds minimal fields: transport type (Moto/Bus), recipient contact information, and delivery notes. In contrast, `InternationalShipment` extends with destination country, customs declaration, estimated value for duty calculation, and a related `CustomsDocument` model for storing passport, TIN, and invoice details. This separation eliminates "ghost fields"—nullable columns that exist in a unified model but only apply to one shipment type.

## Validation Strategy

Validation logic resides in the `core/validators.py` module as independent, type-annotated functions. The `validate_rwanda_phone()` function uses regex pattern matching to ensure numbers start with +250 and follow valid network codes (78X for MTN, 72X/73X for Airtel). The `validate_rwanda_nid()` function performs multi-step validation: checking length (exactly 16 digits), verifying the leading '1', validating birth year range (1900-2010), and computing the Luhn checksum algorithm.

For international shipments, `validate_tin()` enforces 9-digit numeric format, while `validate_passport()` checks alphanumeric structure between 6-9 characters. These validators are called in serializer `validate_*` methods, ensuring that validation errors return meaningful HTTP 400 responses with field-specific error messages.

## Status Flow Differences

The status lifecycle differs significantly between shipment types. Domestic shipments follow a linear progression: PENDING → PICKED_UP → IN_TRANSIT → DELIVERED. International shipments introduce customs stages: PENDING → PICKED_UP → IN_TRANSIT → AT_CUSTOMS → CLEARED_CUSTOMS → DELIVERED. Attempting to represent both flows in a single model would require complex state machine logic and conditional status transitions.

By maintaining separate models, each shipment type has its own STATUS_CHOICES tuple. The `InternationalShipment` model extends the base choices with customs-specific statuses, making it impossible for a domestic shipment to incorrectly enter a customs state.

## User Experience Implications

This architectural separation directly improves user experience. When a customer creates a domestic shipment via the mobile app, they encounter a simple 3-field form (origin, destination, weight). The API endpoint `/api/domestic/shipments/` returns only relevant fields in the response payload, minimizing data transfer for agents on rural 2G networks.

International shipments present a more complex 10+ field form through `/api/international/shipments/`, but this complexity is justified by customs requirements. The response includes nested `customs_documents` arrays, but this data is essential for tracking customs clearance progress. Mobile agents can filter international shipments by `destination_country` to quickly identify cross-border packages requiring special handling.

## Performance and Scalability

Separate tables enable database-level optimizations. Domestic shipments represent approximately 80% of transaction volume (high frequency, low complexity), while international shipments account for 20% (low frequency, high complexity). Database indexes can be tailored to each access pattern. The `domestic_shipments` table has indexes on `tracking_number` and `status` for rapid mobile queries. The `international_shipments` table adds indexes on `destination_country` and `status` for border hub manifest generation.

Query performance benefits significantly. A domestic shipment list query never joins the `customs_documents` table, reducing join complexity. Conversely, international shipment queries can use `select_related('customs_documents')` to efficiently fetch nested data without N+1 query problems.

## Future Extensibility

This modular architecture supports future business expansion. If IshemaLink adds air freight services, we can create an `airfreight/` app with its own validation rules (IATA cargo codes, airline waybills) without modifying existing domestic or international code. Each app remains independently testable and deployable.

Similarly, if Rwanda signs new trade agreements expanding EAC to COMESA (Common Market for Eastern and Southern Africa), the international app can be extended with new `destination_country` choices and corresponding customs validators without risk of breaking domestic shipment logic.

## Conclusion

The separation of domestic and international shipment logic reflects real-world regulatory boundaries rather than arbitrary technical decisions. By structuring the codebase around these regulatory domains, the IshemaLink API achieves type safety, performance optimization, and maintainability. Each shipment type has its own validation rules, status workflows, and API endpoints, making the system easier to reason about, test, and extend. This architectural choice demonstrates that good software design aligns with business domain boundaries.

---


