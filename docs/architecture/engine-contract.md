# Engine contract

Each engine should have a stable identifier, version, capabilities, validated inputs, structured outputs, explicit errors, and tests.

The registry exposes metadata; it must not contain engine business logic. Routes orchestrate calls and translate known errors into HTTP responses.

To add an engine, create `backend/src/mayachitram/engines/<name>/`, implement schemas and service, isolate provider code under `providers/`, register metadata, add API routes and tests, then add frontend features only if a UI is needed.
