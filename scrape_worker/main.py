from __future__ import annotations

import asyncio
import logging


def main() -> None:
    from scrape_worker.worker import run

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.getLogger("scrape_worker").info("Worker stopped by user.")


if __name__ == "__main__":
    main()
