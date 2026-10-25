# ADR 0002: Provider adapters

- Status: Accepted
- Date: 2026-10-25

Keep vendor SDK calls inside provider adapters. The Image Engine and public API consume engine-level schemas, allowing provider changes without changing the frontend contract. Avoid building a generic plugin framework until real requirements justify it.
