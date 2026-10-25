# Adding an engine

1. Create `backend/src/mayachitram/engines/<name>/`.
2. Define typed schemas.
3. Implement engine logic in `service.py`.
4. Isolate external SDK calls under `providers/`.
5. Register public metadata in `platform/registry.py`.
6. Add versioned API routes and tests.
7. Add a frontend feature under `frontend/src/features/<name>/` if required.
8. Update API docs and changelog.

Avoid importing another engine's internals. Promote genuinely shared behavior to a small, tested platform module.
