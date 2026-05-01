def feature_flag_payload(*, key: str = "test_flag") -> dict[str, object]:
    return {
        "key": key,
        "name": "Test Flag",
        "description": "Flag used by integration tests",
        "is_enabled": True,
        "is_public": False,
    }
