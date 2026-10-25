from pathlib import Path

required = [
    "frontend/package.json",
    "frontend/src/app/App.tsx",
    "backend/pyproject.toml",
    "backend/src/mayachitram/main.py",
    "backend/src/mayachitram/engines/image/service.py",
    "docs/architecture/overview.md",
    "docker-compose.yml",
]
missing = [item for item in required if not Path(item).is_file()]
if missing:
    raise SystemExit(f"Missing required project files: {missing}")
print(f"Structure check passed ({len(required)} required files).")
