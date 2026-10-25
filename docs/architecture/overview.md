# Architecture overview

## Frontend
Owns navigation, image upload interaction, loading/error states, and result presentation. It never holds provider keys or calls model providers directly.

## Backend API
Owns HTTP validation, API versioning, request orchestration, and stable client-facing schemas.

## Platform
Owns cross-engine concerns such as engine discovery and registration. Shared capabilities should be introduced when multiple engines need them.

## Engines
Own engine-specific schemas, application logic, and provider adapters. The first engine is `image`.

## Providers
Wrap vendor SDKs and normalize responses into engine-level schemas. Provider SDK types should not leak into API contracts.

## Deployment
A monorepo with two applications and a modular-monolith backend. Deploy frontend/backend independently if needed. Split engines into services only when operational evidence justifies it.
