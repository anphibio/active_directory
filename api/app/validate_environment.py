import json
import sys

from app.config import get_settings


def main() -> int:
    settings = get_settings()
    summary = settings.safe_summary()
    production_errors = settings.production_errors()
    summary["production_ready"] = not production_errors
    summary["production_errors"] = production_errors
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ad_ready_for_connection_test"] and not production_errors else 1


if __name__ == "__main__":
    sys.exit(main())
