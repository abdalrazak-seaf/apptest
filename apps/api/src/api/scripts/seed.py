"""Load development seed data. Usage: uv run python -m api.scripts.seed

Phase 0 has no tables yet. Phase 1 adds the Saudi city list and vehicle taxonomy here.
Seed data only comes from files in this repo or data the product owner supplies.
Never scrape other platforms.
"""

import logging

from api.core.config import get_settings
from api.core.logging import configure_logging

logger = logging.getLogger("api.seed")


def main() -> None:
    configure_logging(get_settings().log_level)
    logger.info("seed_complete", extra={"seeded": []})


if __name__ == "__main__":
    main()
