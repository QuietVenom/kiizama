from __future__ import annotations

import asyncio
import logging

from scrape_worker.bootstrap import setup_backend_context


def main() -> None:
    setup_backend_context()

    from scrape_worker.config import apply_backend_compat_env, get_settings

    apply_backend_compat_env(get_settings())

    # Import after bootstrap to guarantee backend modules are resolvable.
    from scrape_worker.worker import run

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.getLogger("scrape_worker").info("Worker stopped by user.")


if __name__ == "__main__":
    main()
