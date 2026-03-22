import uuid

from app.core.ids import generate_uuid7


def test_generate_uuid7_returns_stdlib_uuid_v7() -> None:
    generated = generate_uuid7()

    assert isinstance(generated, uuid.UUID)
    assert generated.version == 7


def test_generate_uuid7_is_unique() -> None:
    first = generate_uuid7()
    second = generate_uuid7()

    assert first != second
