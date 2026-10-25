# ADR 0001: Modular monolith

- Status: Accepted
- Date: 2026-10-25

The platform needs multiple engines, but early development does not justify independently deployed microservices. Use one backend with explicit platform and engine boundaries, and a separate frontend application. This simplifies operations while preserving a path to extraction if evidence later warrants it.
