from kiizama_scrape_core.sql import create_sqlmodel_engine
from kiizama_scrape_core.sql import ping_postgres as core_ping_postgres

from scrape_worker.config import get_settings

engine = create_sqlmodel_engine(get_settings().database_url)


def ping_postgres() -> None:
    core_ping_postgres(engine)


__all__ = ["engine", "ping_postgres"]
