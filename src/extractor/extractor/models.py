"""Pydantic models for clauses, sections, and serialization.

The internal :class:`Clause` carries provenance fields (section, ordinal, page
range, kept/struck char counts) used by the eval and verifier; the wire-format
adapter :func:`to_spec_dict` strips those down to the README-mandated triple
``{id, title, text}``.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Section(StrEnum):
    """One of the three numbering ranges concatenated inside Part II."""

    SHELLVOY = "shellvoy"
    ADDITIONAL = "additional"
    ESSAR = "essar"


class Clause(BaseModel):
    """A single extracted clause, with full provenance."""

    section: Section
    ordinal: int = Field(ge=1, description="The N. as printed in the source PDF.")
    title: str
    text: str
    page_start: int = Field(ge=1, description="1-indexed PDF page where the clause begins.")
    page_end: int = Field(ge=1, description="1-indexed PDF page where the clause ends.")

    @field_validator("title", "text")
    @classmethod
    def _strip_whitespace(cls, value: str) -> str:
        return value.strip()

    @property
    def id(self) -> str:
        """Globally-unique clause identifier — section-prefixed ordinal.

        We disambiguate the three resets in numbering with a section prefix
        (e.g. ``shellvoy-1`` vs ``additional-1`` vs ``essar-1``) so that the
        flat JSON list stays index-able and free of collisions.
        """
        return f"{self.section.value}-{self.ordinal}"

    def to_spec_dict(self) -> dict[str, str]:
        """Serialize to the wire format mandated by the README."""
        return {"id": self.id, "title": self.title, "text": self.text}
