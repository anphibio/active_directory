import json
import sys
from datetime import UTC, datetime

from app.database import apply_migrations, available_migrations


def main() -> int:
    try:
        applied = apply_migrations()
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "ok",
            "available": [migration.stem for migration in available_migrations()],
            "applied": applied,
        }
        print(json.dumps(payload))
        return 0
    except Exception as exc:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "error",
            "error": exc.__class__.__name__,
        }
        print(json.dumps(payload))
        return 1


if __name__ == "__main__":
    sys.exit(main())
