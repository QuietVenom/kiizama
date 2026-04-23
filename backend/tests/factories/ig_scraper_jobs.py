def scrape_job_payload(*, usernames: list[str] | None = None) -> dict[str, object]:
    return {"usernames": usernames or ["alpha", "beta"]}
