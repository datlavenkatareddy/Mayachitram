# API overview

Base URL: `http://localhost:8000`

- `GET /health` — process health.
- `GET /api/v1/engines` — registered engine metadata.
- `POST /api/v1/image/analyze` — multipart upload, field `file`.

Accepted formats: JPEG, PNG, WebP. Maximum size: `MAX_UPLOAD_BYTES`, default 10 MiB.

Successful response contains `engine`, `provider`, `model`, `description`, `objects`, and `caveats`. Expected errors: 400 invalid image, 413 oversized upload, 503 missing provider configuration, 502 provider failure.
