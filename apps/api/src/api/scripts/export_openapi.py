"""Write the OpenAPI spec used to generate packages/api-client.

Usage: uv run python -m api.scripts.export_openapi <output.json>
"""

import json
import sys
from pathlib import Path

from api.main import create_app


def main() -> None:
    spec = create_app().openapi()
    output = json.dumps(spec, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    main()
