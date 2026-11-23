"""Write the API's OpenAPI schema to frontend/types/openapi.json.

The Pydantic models in app/ are the only definition of the trip types. The
website's TypeScript types are generated from this file, so they can't drift:

    python scripts/export_openapi.py          # from backend/
    cd ../frontend && npm run types:gen

CI runs both and fails if the committed files differ (scripts/check-types.sh).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api import create_app  # noqa: E402
from app.config import BACKEND_DIR  # noqa: E402

OUT = BACKEND_DIR.parent / "frontend" / "types" / "openapi.json"


def main() -> None:
    schema = create_app().openapi()
    OUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(BACKEND_DIR.parent)}")


if __name__ == "__main__":
    main()
