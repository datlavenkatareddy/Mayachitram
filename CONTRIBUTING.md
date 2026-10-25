# Contributing

- Keep frontend and backend dependencies separate.
- Keep engine-specific behavior inside `backend/src/mayachitram/engines/<name>/`.
- Add tests for behavior changes; update API docs when contracts change.
- Never commit secrets, real user images, or local `.env` files.
- Record significant architectural changes in `docs/decisions/`.

Before submitting:
```bash
cd backend && pytest && ruff check .
cd frontend && npm test && npm run build
```
