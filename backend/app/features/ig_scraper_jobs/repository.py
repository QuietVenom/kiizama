from kiizama_scrape_core.ig_scraper_v2.persistence import (
    SqlInstagramJobProjectionRepositoryV2,
)

SqlInstagramJobProjectionRepository = SqlInstagramJobProjectionRepositoryV2
SqlJobProjectionRepository = SqlInstagramJobProjectionRepositoryV2

__all__ = [
    "SqlInstagramJobProjectionRepository",
    "SqlInstagramJobProjectionRepositoryV2",
    "SqlJobProjectionRepository",
]
