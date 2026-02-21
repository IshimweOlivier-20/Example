# IshemaLink Architecture

## System Overview


graph TD
    Mobile[Mobile App] --> API[API Gateway]
    Web[Web Dashboard] --> API
    Gov[Gov Auditor Portal] --> API

    API --> Auth[Hybrid Auth]
    API --> Booking[Booking Service]
    API --> Payment[Payment Service]
    API --> Notify[Notification Service]
    API --> Analytics[BI Queries]

    Booking --> DB[(PostgreSQL)]
    Payment --> DB
    Analytics --> DB

    API --> Cache[(Redis Cache)]
    API --> WS[WebSocket Tracking]

    Payment --> RRA[RRA EBM API]
    Booking --> RURA[RURA License API]
    Booking --> Customs[Customs API]

    Notify --> SMS[SMS Gateway]

    WS --> Mobile
    WS --> Web
```

## Key Design Choices

- ACID booking flow with payment confirmation and driver assignment.
- Raw SQL analytics for MINICOM reporting with privacy-preserving aggregates.
- Government connectors abstracted behind service interfaces.
- WebSocket tracking for live updates, HTTP fallback via REST.

## Data Privacy and Compliance

- Field-level encryption for NID/Tax ID.
- Audit log middleware for sensitive data access.
- Role-based access for agents, drivers, admins, and gov officials.
