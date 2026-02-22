"""Pydantic schemas for the feature template."""

from pydantic import BaseModel


class ExampleSchema(BaseModel):
    name: str


__all__ = ["ExampleSchema"]
